module pwm_generator #(
    parameter int PERIOD = 6666
)(
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] duty_cycle,
    input  logic       dir_in,
    output logic       dir_out,
    output logic       pwm_out
);
    logic [13:0] cout;
    logic [13:0] duty_threshold;

    assign duty_threshold = (PERIOD * duty_cycle) >> 8;
    assign dir_out = dir_in;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cout    <= 14'd0;
            pwm_out <= 1'b0;
        end else begin
            if (cout >= PERIOD - 1)
                cout <= 14'd0;
            else
                cout <= cout + 1'b1;

            if (cout < duty_threshold && duty_cycle != 8'd0)
                pwm_out <= 1'b1;
            else
                pwm_out <= 1'b0;
        end
    end
endmodule
