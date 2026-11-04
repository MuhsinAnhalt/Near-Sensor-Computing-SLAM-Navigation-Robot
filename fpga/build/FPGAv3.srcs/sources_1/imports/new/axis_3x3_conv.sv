`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2026/10/25 17:47:47
// Design Name: 
// Module Name: axis_3x3_conv
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

module axis_3x3_conv #(
    parameter IMG_WIDTH = 1280,
    // 9 个卷积核系数（支持有符号数）
    parameter C00 = 1, parameter C01 = 2, parameter C02 = 1,
    parameter C10 = 2, parameter C11 = 4, parameter C12 = 2,
    parameter C20 = 1, parameter C21 = 2, parameter C22 = 1,
    parameter DATA_WIDTH = 8,   // 输入数据位宽（灰度图为8）
    parameter OUT_WIDTH = 16    // 输出数据位宽（防止乘加溢出，建议16）
)(
    input  logic                   aclk,
    input  logic                   aresetn,
    
    // AXI4-Stream Slave (输入：灰度图)
    input  logic                   s_axis_tvalid,
    output logic                   s_axis_tready,
    input  logic [DATA_WIDTH-1:0]  s_axis_tdata,
    input  logic                   s_axis_tuser,
    input  logic                   s_axis_tlast,
    
    // AXI4-Stream Master (输出：卷积特征图)
    output logic                   m_axis_tvalid,
    input  logic                   m_axis_tready,
    output logic [OUT_WIDTH-1:0]   m_axis_tdata,
    output logic                   m_axis_tuser,
    output logic                   m_axis_tlast
);

    // ==========================================
    // 1. 行缓存与地址控制
    // ==========================================
    logic [10:0] wr_addr; // 最大支持 2048 宽度
    logic [DATA_WIDTH-1:0] ram1 [0:IMG_WIDTH-1];
    logic [DATA_WIDTH-1:0] ram2 [0:IMG_WIDTH-1];
    
    logic [DATA_WIDTH-1:0] line1_data;
    logic [DATA_WIDTH-1:0] line2_data;

    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            wr_addr <= 0;
        end else if (s_axis_tvalid && s_axis_tready) begin
            if (s_axis_tuser) 
                wr_addr <= 0;
            else if (wr_addr == IMG_WIDTH - 1) 
                wr_addr <= 0;
            else 
                wr_addr <= wr_addr + 1;
        end
    end

    // 写入 BRAM（跳过第一行，第一行不需要缓存，因为它是上上行）
    always_ff @(posedge aclk) begin
        if (s_axis_tvalid && s_axis_tready) begin
            if (!s_axis_tuser) begin // 注意帧首屏蔽
                ram1[wr_addr] <= s_axis_tdata;
                ram2[wr_addr] <= ram1[wr_addr]; // ram1 读出后存入 ram2
            end
        end
    end

    // 读出 BRAM（同步读，1个周期延迟）
    always_ff @(posedge aclk) begin
        line1_data <= ram1[wr_addr];
        line2_data <= ram2[wr_addr];
    end

    // ==========================================
    // 2. 生成 3x3 窗口 (打拍)
    // ==========================================
    // r0: 上上行，r1: 上一行，r2: 当前行
    logic [DATA_WIDTH-1:0] r0_0, r0_1, r0_2;
    logic [DATA_WIDTH-1:0] r1_0, r1_1, r1_2;
    logic [DATA_WIDTH-1:0] r2_0, r2_1, r2_2;

    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            {r0_0, r0_1, r0_2} <= '0;
            {r1_0, r1_1, r1_2} <= '0;
            {r2_0, r2_1, r2_2} <= '0;
        end else if (s_axis_tvalid && s_axis_tready) begin
            // 第 2 行（当前输入）
            r2_0 <= r2_1; 
            r2_1 <= r2_2; 
            r2_2 <= s_axis_tdata;
            
            // 第 1 行（上一行）
            r1_0 <= r1_1; 
            r1_1 <= r1_2; 
            r1_2 <= line1_data;
            
            // 第 0 行（上上行）
            r0_0 <= r0_1; 
            r0_1 <= r0_2; 
            r0_2 <= line2_data;
        end
    end

    // ==========================================
    // 3. 乘加运算 (纯组合逻辑/树状加法)
    // ==========================================
    // 使用 signed 防止负数溢出
    logic signed [OUT_WIDTH-1:0] sum;
    
    always_comb begin
        sum = (signed'(r0_0) * C00) + (signed'(r0_1) * C01) + (signed'(r0_2) * C02) +
              (signed'(r1_0) * C10) + (signed'(r1_1) * C11) + (signed'(r1_2) * C12) +
              (signed'(r2_0) * C20) + (signed'(r2_1) * C21) + (signed'(r2_2) * C22);
    end

    // ==========================================
    // 4. 时序对齐与输出控制
    // ==========================================
    // 经过 BRAM 读(1拍) + 窗口打拍(2拍) = 3拍延迟
    logic vld_d1, vld_d2, vld_d3;
    logic usr_d1, usr_d2, usr_d3;
    logic lst_d1, lst_d2, lst_d3;
    logic signed [OUT_WIDTH-1:0] sum_d1, sum_d2, sum_d3;

    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            vld_d1 <= 0; vld_d2 <= 0; vld_d3 <= 0;
            usr_d1 <= 0; usr_d2 <= 0; usr_d3 <= 0;
            lst_d1 <= 0; lst_d2 <= 0; lst_d3 <= 0;
            sum_d1 <= '0; sum_d2 <= '0; sum_d3 <= '0;
        end else if (s_axis_tready) begin
            // 延迟 1 拍
            vld_d1 <= s_axis_tvalid;
            usr_d1 <= s_axis_tuser;
            lst_d1 <= s_axis_tlast;
            sum_d1 <= sum;
            
            // 延迟 2 拍
            vld_d2 <= vld_d1;
            usr_d2 <= usr_d1;
            lst_d2 <= lst_d1;
            sum_d2 <= sum_d1;
            
            // 延迟 3 拍
            vld_d3 <= vld_d2;
            usr_d3 <= usr_d2;
            lst_d3 <= lst_d2;
            sum_d3 <= sum_d2;
        end
    end

    // 流控反压：如果下游没准备好，整个模块不接收新数据
    assign s_axis_tready = m_axis_tready;

    assign m_axis_tvalid = vld_d3;
    assign m_axis_tdata  = sum_d3;
    assign m_axis_tuser  = usr_d3;
    assign m_axis_tlast  = lst_d3;

endmodule
