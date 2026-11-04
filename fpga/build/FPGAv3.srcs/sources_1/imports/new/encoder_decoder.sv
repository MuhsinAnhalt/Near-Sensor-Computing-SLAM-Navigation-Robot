`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2026/09/29 18:40:01
// Design Name: 
// Module Name: encoder_decoder
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module encoder_decoder(
    input logic clk,
    input logic rst_n,
    input logic enc_a,
    input logic enc_b,
    output logic signed [15:0]count,
    output logic dir
    );

    logic a_sync1,a_sync2,b_sync1,b_sync2;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)
        begin
            a_sync1<=0;
            a_sync2<=0;
            b_sync1<=0;
            b_sync2<=0;
        end else 
        begin
            a_sync1<=enc_a;
            a_sync2<=a_sync1;
            b_sync1<=enc_b;
            b_sync2<=b_sync1;
    end
    
    logic [1:0] ab_now, ab_prev;
    assign ab_now={a_sync2,b_sync2};
    always@(posedge clk or negedge rst_n)
    begin
        if(!rst_n)
            ab_prev<=2'b00;
        else
            ab_prev<=ab_now;;
    end
    
    always@(posedge clk or negedge rst_n)
    begin
        if(!rst_n)
        begin
            count<=16'sd0;
            dir<=1'b0;
        end else
            case({ab_prev,ab_now})
            4'b0010,4'b1011,4'b1101,4'b0100:
                begin
                count<=count+1;
                dir<=1'b1;
                end
            4'b0001,4'b0111,4'b1110,4'b1000:
                begin
                count<=count-1;
                dir<=1'b0;
                end
            default: 
            begin
                count <= count;
                dir   <= dir;
            end 
            endcase
    end
endmodule