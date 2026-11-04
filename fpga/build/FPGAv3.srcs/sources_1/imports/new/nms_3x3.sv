`timescale 1ns / 1ps
module nms_3x3 (
    input  logic        aclk,
    input  logic        aresetn,
    
    input  logic [8:0]  s_p00, s_p01, s_p02,
    input  logic [8:0]  s_p10, s_p11, s_p12,
    input  logic [8:0]  s_p20, s_p21, s_p22,
    input  logic [1:0]  s_dir,
    
    input  logic        s_axis_tvalid,
    output logic        s_axis_tready,
    input  logic        s_axis_tuser,
    input  logic        s_axis_tlast,
    
    output logic [8:0]  m_axis_tdata,
    output logic        m_axis_tvalid,
    input  logic        m_axis_tready,
    output logic        m_axis_tuser,
    output logic        m_axis_tlast
);

    logic [8:0] mag_a, mag_b, mag_out;
    
    always_comb begin
        case(s_dir)
            2'b00: begin mag_a = s_p10; mag_b = s_p12; end // 左右
            2'b01: begin mag_a = s_p01; mag_b = s_p21; end // 上下
            2'b10: begin mag_a = s_p02; mag_b = s_p20; end // 左下右上
            2'b11: begin mag_a = s_p00; mag_b = s_p22; end // 左上右下
            default: begin mag_a = '0; mag_b = '0; end
        endcase
        
        if (s_p11 >= mag_a && s_p11 >= mag_b) mag_out = s_p11;
        else mag_out = '0;
    end
    
    assign s_axis_tready = m_axis_tready;
    
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            m_axis_tvalid <= 0; m_axis_tdata <= 0; m_axis_tuser <= 0; m_axis_tlast <= 0;
        end else if (s_axis_tvalid && s_axis_tready) begin
            m_axis_tvalid <= 1; m_axis_tdata <= mag_out; m_axis_tuser <= s_axis_tuser; m_axis_tlast <= s_axis_tlast;
        end else if (m_axis_tready) begin
            m_axis_tvalid <= 0;
        end
    end
endmodule