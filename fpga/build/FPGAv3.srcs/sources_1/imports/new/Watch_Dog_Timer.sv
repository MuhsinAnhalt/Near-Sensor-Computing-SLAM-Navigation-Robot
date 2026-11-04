`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2026/10/17 14:23:44
// Design Name: 
// Module Name: Watch_Dog_Timer
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


module Watch_Dog_Timer #(
parameter TIMEOUT_CNT_MAX = 20_000_000
)(
    input logic clk,
    input logic rst_n,
    input logic cmd_valid,
    output logic safe_stop
    );
    
    logic [24:0]timeout_cnt;
    always@(posedge clk or negedge rst_n)
    begin
        if (!rst_n)
            timeout_cnt <= 25'd0;
        else if (cmd_valid)
            timeout_cnt <= 25'd0;
        else if (timeout_cnt >= TIMEOUT_CNT_MAX)
            timeout_cnt <= timeout_cnt;
        else
            timeout_cnt <= timeout_cnt + 1'b1;
    end
    
    always @(posedge clk or negedge rst_n)
    begin
        if (!rst_n)
            safe_stop <= 1'b0;
        else if(cmd_valid)
            safe_stop <= 1'b0;
        else if (timeout_cnt >= TIMEOUT_CNT_MAX - 1) 
            safe_stop <= 1'b1;
        else
            safe_stop <= safe_stop;
    end
        
endmodule
