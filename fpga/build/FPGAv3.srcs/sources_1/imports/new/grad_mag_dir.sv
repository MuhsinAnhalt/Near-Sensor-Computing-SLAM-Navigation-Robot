`timescale 1ns / 1ps
module grad_mag_dir (
    input  logic        aclk,
    input  logic        aresetn,
    
    // Gx 输入流
    input  logic        s_axis_gx_tvalid,
    output logic        s_axis_gx_tready,
    input  logic [9:0]  s_axis_gx_tdata, // 10-bit signed
    input  logic        s_axis_gx_tuser,
    input  logic        s_axis_gx_tlast,
    
    // Gy 输入流
    input  logic        s_axis_gy_tvalid,
    output logic        s_axis_gy_tready,
    input  logic [9:0]  s_axis_gy_tdata, // 10-bit signed
    input  logic        s_axis_gy_tuser,
    input  logic        s_axis_gy_tlast,
    
    // 输出流
    output logic        m_axis_tvalid,
    input  logic        m_axis_tready,
    output logic [8:0]  m_axis_tdata_mag, // 9-bit unsigned
    output logic [1:0]  m_axis_tdata_dir,
    output logic        m_axis_tuser,
    output logic        m_axis_tlast
);

    logic signed [9:0] gx_abs, gy_abs;
    logic [8:0] mag;
    logic [1:0] dir;
    
    always_comb begin
        gx_abs = s_axis_gx_tdata[9] ? -s_axis_gx_tdata : s_axis_gx_tdata;
        gy_abs = s_axis_gy_tdata[9] ? -s_axis_gy_tdata : s_axis_gy_tdata;
        mag = gx_abs[8:0] + gy_abs[8:0];
        
        // 方向量化
        if (gx_abs > (gy_abs << 1)) dir = 2'b00;       // 水平
        else if (gy_abs > (gx_abs << 1)) dir = 2'b01;  // 垂直
        else if (s_axis_gx_tdata[9] == s_axis_gy_tdata[9]) dir = 2'b10; // 45度
        else dir = 2'b11; // 135度
    end
    
    assign s_axis_gx_tready = m_axis_tready;
    assign s_axis_gy_tready = m_axis_tready;
    
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            m_axis_tvalid <= 0;
            m_axis_tdata_mag <= 0;
            m_axis_tdata_dir <= 0;
            m_axis_tuser <= 0;
            m_axis_tlast <= 0;
        end else if (s_axis_gx_tvalid && s_axis_gy_tvalid && s_axis_gx_tready) begin
            m_axis_tvalid <= 1;
            m_axis_tdata_mag <= mag;
            m_axis_tdata_dir <= dir;
            m_axis_tuser <= s_axis_gx_tuser;
            m_axis_tlast <= s_axis_gx_tlast;
        end else if (m_axis_tready) begin
            m_axis_tvalid <= 0;
        end
    end
endmodule