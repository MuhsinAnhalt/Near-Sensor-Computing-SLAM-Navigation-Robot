`timescale 1ns / 1ps
module mag_line_buffer #(
    parameter IMG_WIDTH = 1280
)(
    input  logic        aclk,
    input  logic        aresetn,
    
    input  logic        s_axis_tvalid,
    output logic        s_axis_tready,
    input  logic [8:0]  s_axis_tdata,
    input  logic        s_axis_tuser,
    input  logic        s_axis_tlast,
    
    output logic [8:0]  m_p00, m_p01, m_p02,
    output logic [8:0]  m_p10, m_p11, m_p12,
    output logic [8:0]  m_p20, m_p21, m_p22,
    output logic        m_axis_tvalid,
    input  logic        m_axis_tready,
    output logic        m_axis_tuser,
    output logic        m_axis_tlast
);

    logic [10:0] wr_addr;
    logic [8:0]  ram1 [0:IMG_WIDTH-1];
    logic [8:0]  ram2 [0:IMG_WIDTH-1];
    
    logic [8:0] line1_data, line2_data;
    
    // 读写地址控制
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) wr_addr <= 0;
        else if (s_axis_tvalid && s_axis_tready) begin
            if (s_axis_tuser) wr_addr <= 0;
            else if (wr_addr == IMG_WIDTH - 1) wr_addr <= 0;
            else wr_addr <= wr_addr + 1;
        end
    end
    
    // 双口 RAM 写入
    always_ff @(posedge aclk) begin
        if (s_axis_tvalid && s_axis_tready && !s_axis_tuser) begin
            ram1[wr_addr[9:0]] <= s_axis_tdata;
            ram2[wr_addr[9:0]] <= ram1[wr_addr[9:0]];
        end
    end
    
    // 双口 RAM 读出 (同步读)
    always_ff @(posedge aclk) begin
        line1_data <= ram1[wr_addr[9:0]];
        line2_data <= ram2[wr_addr[9:0]];
    end
    
    // 构造 3x3 窗口
    logic [8:0] r0_0, r0_1, r0_2;
    logic [8:0] r1_0, r1_1, r1_2;
    logic [8:0] r2_0, r2_1, r2_2;
    
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            {r0_0, r0_1, r0_2} <= '0; {r1_0, r1_1, r1_2} <= '0; {r2_0, r2_1, r2_2} <= '0;
        end else if (s_axis_tvalid && s_axis_tready) begin
            r0_0 <= r0_1; r0_1 <= r0_2; r0_2 <= line2_data;
            r1_0 <= r1_1; r1_1 <= r1_2; r1_2 <= line1_data;
            r2_0 <= r2_1; r2_1 <= r2_2; r2_2 <= s_axis_tdata;
        end
    end
    
    assign m_p00 = r0_0; assign m_p01 = r0_1; assign m_p02 = r0_2;
    assign m_p10 = r1_0; assign m_p11 = r1_1; assign m_p12 = r1_2;
    assign m_p20 = r2_0; assign m_p21 = r2_1; assign m_p22 = r2_2;
    
    assign s_axis_tready = m_axis_tready;
    
    // 数据流控制同步延迟
    // 流控：valid跟RAM的读出延迟对齐
    logic vld_d1;
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) vld_d1 <= 0;
        else if (s_axis_tready) vld_d1 <= s_axis_tvalid;
    end
    
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            m_axis_tvalid <= 0; m_axis_tuser <= 0; m_axis_tlast <= 0;
        end else if (vld_d1) begin
            m_axis_tvalid <= 1; m_axis_tuser <= s_axis_tuser; m_axis_tlast <= s_axis_tlast;
        end else if (m_axis_tready) begin
            m_axis_tvalid <= 0;
        end
    end
endmodule