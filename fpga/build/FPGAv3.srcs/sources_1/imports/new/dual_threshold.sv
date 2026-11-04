`timescale 1ns / 1ps
module dual_threshold (
    input  logic        aclk,
    input  logic        aresetn,
    
    input  logic [8:0]  s_axis_tdata,
    input  logic        s_axis_tvalid,
    output logic        s_axis_tready,
    input  logic        s_axis_tuser,
    input  logic        s_axis_tlast,
    
    output logic [1:0]  m_axis_tdata,
    output logic        m_axis_tvalid,
    input  logic        m_axis_tready,
    output logic        m_axis_tuser,
    output logic        m_axis_tlast,
    
    input  logic [7:0]  th_high,
    input  logic [7:0]  th_low
);

    logic [1:0] edge_type;
    
    always_comb begin
        if (s_axis_tdata >= {1'b0, th_high}) edge_type = 2'b11;
        else if (s_axis_tdata >= {1'b0, th_low}) edge_type = 2'b01;
        else edge_type = 2'b00;
    end
    
    assign s_axis_tready = m_axis_tready;
    
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            m_axis_tvalid <= 0; m_axis_tdata <= 0; m_axis_tuser <= 0; m_axis_tlast <= 0;
        end else if (s_axis_tvalid && s_axis_tready) begin
            m_axis_tvalid <= 1; m_axis_tdata <= edge_type; m_axis_tuser <= s_axis_tuser; m_axis_tlast <= s_axis_tlast;
        end else if (m_axis_tready) begin
            m_axis_tvalid <= 0;
        end
    end
endmodule