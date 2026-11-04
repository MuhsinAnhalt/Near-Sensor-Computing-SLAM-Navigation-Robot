`timescale 1ns / 1ps

module top(
    input  logic        clk,
    input  logic        rst_n,
    output logic        pwm_l_out,
    output logic        pwm_r_out,
    output logic        dir_l_out,
    output logic        dir_r_out,
    input  logic        enc_a_l,
    input  logic        enc_b_l,
    input  logic        enc_a_r,
    input  logic        enc_b_r,
    output logic [31:0] enc_bus_out,
    input  logic [31:0] ctrl_bus_i
);

    // 必须显式声明宽度！
    logic        cmd_valid;
    logic [7:0]  duty_l;
    logic [7:0]  duty_r;
    logic        dir_l_in;
    logic        dir_r_in;
    logic [15:0] count_l_out;
    logic [15:0] count_r_out;
    logic        pwm_l_raw, pwm_r_raw;
    logic        dir_l_raw, dir_r_raw;
    logic        safe_stop_sig;

    assign cmd_valid = ctrl_bus_i[0];
    assign duty_l    = ctrl_bus_i[8:1];
    assign duty_r    = ctrl_bus_i[16:9];
    assign dir_l_in  = ctrl_bus_i[17];
    assign dir_r_in  = ctrl_bus_i[18];
    assign enc_bus_out = {count_r_out, count_l_out};

    Watch_Dog_Timer #(
        .TIMEOUT_CNT_MAX(20_000_000) 
    ) u_watchdog (
        .clk(clk), 
        .rst_n(rst_n), 
        .cmd_valid(cmd_valid), 
        .safe_stop(safe_stop_sig)
    );

    pwm_generator #(.PERIOD(6666)) u_pwm_left (
        .clk(clk), 
        .rst_n(rst_n), 
        .duty_cycle(duty_l),
        .dir_in(dir_l_in), 
        .dir_out(dir_l_raw), 
        .pwm_out(pwm_l_raw)
    );

    pwm_generator #(.PERIOD(6666)) u_pwm_right (
        .clk(clk), 
        .rst_n(rst_n), 
        .duty_cycle(duty_r),
        .dir_in(dir_r_in), 
        .dir_out(dir_r_raw), 
        .pwm_out(pwm_r_raw)
    );


    assign pwm_l_out = pwm_l_raw & ~safe_stop_sig;
    assign pwm_r_out = pwm_r_raw & ~safe_stop_sig;

    assign dir_l_out = dir_l_raw;
    assign dir_r_out = dir_r_raw;

    encoder_decoder u_enc_left (
        .clk(clk), .rst_n(rst_n), .enc_a(enc_a_l), .enc_b(enc_b_l),
        .count(count_l_out), .dir()
    );
    encoder_decoder u_enc_right (
        .clk(clk), .rst_n(rst_n), .enc_a(enc_a_r), .enc_b(enc_b_r),
        .count(count_r_out), .dir()
    );
endmodule
