`timescale 1ns / 1ps
module edge_tracking #(
    parameter IMG_WIDTH = 1280
)(
    input  logic        aclk,
    input  logic        aresetn,
    
    input  logic [1:0]  s_axis_tdata,
    input  logic        s_axis_tvalid,
    output logic        s_axis_tready,
    input  logic        s_axis_tuser,
    input  logic        s_axis_tlast,
    
    output logic        m_axis_tdata,
    output logic        m_axis_tvalid,
    input  logic        m_axis_tready,
    output logic        m_axis_tuser,
    output logic        m_axis_tlast
);

    logic [10:0] wr_addr;
    logic [1:0]  ram [0:IMG_WIDTH-1];
    logic [1:0]  prev_row_pix;
    
    // 地址控制
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) wr_addr <= 0;
        else if (s_axis_tvalid && s_axis_tready) begin
            if (s_axis_tuser) wr_addr <= 0;
            else if (wr_addr == IMG_WIDTH - 1) wr_addr <= 0;
            else wr_addr <= wr_addr + 1;
        end
    end
    
    // 写/读 BRAM
    always_ff @(posedge aclk) begin
        if (s_axis_tvalid && s_axis_tready && !s_axis_tuser) begin
            ram[wr_addr[9:0]] <= s_axis_tdata;
        end
        prev_row_pix <= ram[wr_addr[9:0]];
    end
    
    // 构建 3x3 窗口
    logic [1:0] r0_0, r0_1, r0_2; // 上一行
    logic [1:0] r1_0, r1_1, r1_2; // 当前行
    logic [1:0] r2_0, r2_1, r2_2; // 下一行
   
    
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            r0_0 <= 0; r0_1 <= 0; r0_2 <= 0;
            r1_0 <= 0; r1_1 <= 0; r1_2 <= 0;
        end else if (s_axis_tvalid && s_axis_tready) begin
            r0_0 <= r0_1; r0_1 <= r0_2; r0_2 <= prev_row_pix; // 上一行
            r1_0 <= r1_1; r1_1 <= r1_2; r1_2 <= s_axis_tdata; // 当前行
        end
    end
    
    logic has_strong;
    always_comb begin
        has_strong = (r0_0 == 2'b11) || (r0_1 == 2'b11) || (r0_2 == 2'b11) || (r1_0 == 2'b11);
    end
    
    logic edge_out;
    always_comb begin
        if (r1_1 == 2'b11) edge_out = 1'b1; // 自身强边缘
        else if (r1_1 == 2'b01 && has_strong) edge_out = 1'b1; // 弱边缘且邻居有强边缘
        else edge_out = 1'b0;
    end
    
    assign s_axis_tready = m_axis_tready;
    
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            m_axis_tvalid <= 0; m_axis_tdata <= 0; m_axis_tuser <= 0; m_axis_tlast <= 0;
        end else if (s_axis_tvalid && s_axis_tready) begin
            m_axis_tvalid <= 1; m_axis_tdata <= edge_out; m_axis_tuser <= s_axis_tuser; m_axis_tlast <= s_axis_tlast;
        end else if (m_axis_tready) begin
            m_axis_tvalid <= 0;
        end
    end
endmodule