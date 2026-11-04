`timescale 1ns / 1ps
module rle_encoder (
    input  logic        aclk,
    input  logic        aresetn,
    
    input  logic        s_axis_tdata,
    input  logic        s_axis_tvalid,
    output logic        s_axis_tready,
    input  logic        s_axis_tuser,
    input  logic        s_axis_tlast,
    
    output logic [15:0] m_axis_tdata,
    output logic        m_axis_tvalid,
    input  logic        m_axis_tready,
    output logic        m_axis_tuser,
    output logic        m_axis_tlast
);

    logic [7:0] run_len;
    logic       cur_pix;
    
    // 输出寄存器
    logic [15:0] out_data;
    logic        out_tlast; // 独立出来的 tlast 寄存器
    logic        out_valid;
    
    // AXI-Stream 标准握手：如果输出空着或者下游能接，就接收新数据
    assign s_axis_tready = (out_valid == 1'b0) || m_axis_tready;
    
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            run_len   <= 8'd0; 
            cur_pix   <= 1'b0;
            out_valid <= 1'b0; 
            out_data  <= 16'd0;
            out_tlast <= 1'b0;
        end else begin
            if (s_axis_tvalid && s_axis_tready) begin
                if (s_axis_tuser) begin
                    run_len   <= 8'd1;
                    cur_pix   <= s_axis_tdata;
                    out_valid <= 1'b0;
                end else if (s_axis_tdata == cur_pix && run_len < 255) begin
                    run_len <= run_len + 1'b1;
                    if (s_axis_tlast) begin
                        // 行结束，强制输出（注意位宽：7'b0 + 1'b1 + 8位 = 16位）
                        out_data <= {s_axis_tlast, 6'b0, cur_pix, run_len}; 
                        out_tlast <= 1'b1; // 独立标记行尾
                        out_valid <= 1'b1;
                        run_len   <= 8'd0;
                    end
                end else begin
                    // 像素变化或达到255，输出当前统计
                    out_data  <= {7'b0, cur_pix, run_len};
                    out_tlast <= s_axis_tlast;
                    out_valid <= 1'b1;
                    cur_pix   <= s_axis_tdata;
                    run_len   <= 8'd1;
                end
            end else if (out_valid && m_axis_tready) begin
                out_valid <= 1'b0;
                out_tlast <= 1'b0;
            end
        end
    end
    
    assign m_axis_tdata  = out_data;
    assign m_axis_tvalid = out_valid;
    assign m_axis_tuser  = 1'b0; // RLE 不需要 sof
    assign m_axis_tlast  = out_tlast; // 直接输出独立寄存器
endmodule