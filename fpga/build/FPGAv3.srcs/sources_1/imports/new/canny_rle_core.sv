`timescale 1ns / 1ps
module canny_rle_core (
    input  logic        aclk,
    input  logic        aresetn,

    input  logic        s_axis_gray_tvalid,
    output logic        s_axis_gray_tready,
    input  logic [7:0]  s_axis_gray_tdata,
    input  logic        s_axis_gray_tuser,
    input  logic        s_axis_gray_tlast,

    output logic [15:0] m_axis_rle_tdata,
    output logic        m_axis_rle_tvalid,
    input  logic        m_axis_rle_tready,
    output logic        m_axis_rle_tuser,
    output logic        m_axis_rle_tlast,

    input  logic [15:0] th_bus_i
);

    logic [7:0] th_high;
    logic [7:0] th_low;
    assign th_high = th_bus_i[15:8];
    assign th_low  = th_bus_i[7:0];

    logic        gray_tvalid, gray_tready, gray_tuser, gray_tlast;
    logic [7:0]  gray_tdata;

    logic        gaus_tvalid, gaus_tready, gaus_tuser, gaus_tlast;
    logic [11:0] gaus_tdata;

    logic        gx_tvalid, gx_tready, gx_tuser, gx_tlast;
    logic [15:0] gx_tdata;

    logic        gy_tvalid, gy_tready, gy_tuser, gy_tlast;
    logic [15:0] gy_tdata;

    logic        gx_gaus_tready, gy_gaus_tready;

    logic        grad_tvalid, grad_tready, grad_tuser, grad_tlast;
    logic [8:0]  grad_mag;
    logic [1:0]  grad_dir;

    logic        win_tvalid, win_tready, win_tuser, win_tlast;
    logic [8:0]  p00, p01, p02, p10, p11, p12, p20, p21, p22;
    logic        nms_tvalid, nms_tready, nms_tuser, nms_tlast;
    logic [8:0]  nms_mag;

    logic        th_tvalid, th_tready, th_tuser, th_tlast;
    logic [1:0]  th_type;

    logic        edge_tvalid, edge_tready, edge_tuser, edge_tlast;
    logic        edge_pix;

    assign gray_tvalid = s_axis_gray_tvalid;
    assign gray_tdata  = s_axis_gray_tdata;
    assign gray_tuser  = s_axis_gray_tuser;
    assign gray_tlast  = s_axis_gray_tlast;
    assign s_axis_gray_tready = gray_tready;

    assign gaus_tready = gx_gaus_tready & gy_gaus_tready;

    axis_3x3_conv #(
        .IMG_WIDTH(1280),
        .C00(1), .C01(2), .C02(1),
        .C10(2), .C11(4), .C12(2),
        .C20(1), .C21(2), .C22(1),
        .DATA_WIDTH(8), .OUT_WIDTH(12)
    ) u_gaussian (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_tvalid(gray_tvalid), .s_axis_tready(gray_tready),
        .s_axis_tdata(gray_tdata), .s_axis_tuser(gray_tuser), .s_axis_tlast(gray_tlast),
        .m_axis_tvalid(gaus_tvalid), .m_axis_tready(gaus_tready),
        .m_axis_tdata(gaus_tdata), .m_axis_tuser(gaus_tuser), .m_axis_tlast(gaus_tlast)
    );

    axis_3x3_conv #(
        .IMG_WIDTH(1280),
        .C00(-1), .C01(0), .C02(1),
        .C10(-2), .C11(0), .C12(2),
        .C20(-1), .C21(0), .C22(1),
        .DATA_WIDTH(12), .OUT_WIDTH(16)
    ) u_sobel_gx (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_tvalid(gaus_tvalid), .s_axis_tready(gx_gaus_tready),
        .s_axis_tdata(gaus_tdata), .s_axis_tuser(gaus_tuser), .s_axis_tlast(gaus_tlast),
        .m_axis_tvalid(gx_tvalid), .m_axis_tready(gx_tready),
        .m_axis_tdata(gx_tdata), .m_axis_tuser(gx_tuser), .m_axis_tlast(gx_tlast)
    );

    axis_3x3_conv #(
        .IMG_WIDTH(1280),
        .C00(-1), .C01(-2), .C02(-1),
        .C10(0),  .C11(0),  .C12(0),
        .C20(1),  .C21(2),  .C22(1),
        .DATA_WIDTH(12), .OUT_WIDTH(16)
    ) u_sobel_gy (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_tvalid(gaus_tvalid), .s_axis_tready(gy_gaus_tready),
        .s_axis_tdata(gaus_tdata), .s_axis_tuser(gaus_tuser), .s_axis_tlast(gaus_tlast),
        .m_axis_tvalid(gy_tvalid), .m_axis_tready(gy_tready),
        .m_axis_tdata(gy_tdata), .m_axis_tuser(gy_tuser), .m_axis_tlast(gy_tlast)
    );

    grad_mag_dir u_grad (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_gx_tvalid(gx_tvalid), .s_axis_gx_tready(gx_tready),
        .s_axis_gx_tdata(gx_tdata),
        .s_axis_gx_tuser(gx_tuser), .s_axis_gx_tlast(gx_tlast),
        .s_axis_gy_tvalid(gy_tvalid), .s_axis_gy_tready(gy_tready),
        .s_axis_gy_tdata(gy_tdata),
        .s_axis_gy_tuser(gy_tuser), .s_axis_gy_tlast(gy_tlast),
        .m_axis_tvalid(grad_tvalid), .m_axis_tready(grad_tready),
        .m_axis_tdata_mag(grad_mag), .m_axis_tdata_dir(grad_dir),
        .m_axis_tuser(grad_tuser), .m_axis_tlast(grad_tlast)
    );

    mag_line_buffer #(1280) u_buf (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_tvalid(grad_tvalid), .s_axis_tready(grad_tready),
        .s_axis_tdata(grad_mag), .s_axis_tuser(grad_tuser), .s_axis_tlast(grad_tlast),
        .m_p00(p00), .m_p01(p01), .m_p02(p02),
        .m_p10(p10), .m_p11(p11), .m_p12(p12),
        .m_p20(p20), .m_p21(p21), .m_p22(p22),
        .m_axis_tvalid(win_tvalid), .m_axis_tready(win_tready),
        .m_axis_tuser(win_tuser), .m_axis_tlast(win_tlast)
    );

    logic [1:0] dir_dly1, dir_dly2, dir_dly3;
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            dir_dly1 <= 2'b00;
            dir_dly2 <= 2'b00;
            dir_dly3 <= 2'b00;
        end else if (grad_tvalid && grad_tready) begin
            dir_dly1 <= grad_dir;
            dir_dly2 <= dir_dly1;
            dir_dly3 <= dir_dly2;
        end
    end

    nms_3x3 u_nms (
        .aclk(aclk), .aresetn(aresetn),
        .s_p00(p00), .s_p01(p01), .s_p02(p02),
        .s_p10(p10), .s_p11(p11), .s_p12(p12),
        .s_p20(p20), .s_p21(p21), .s_p22(p22),
        .s_dir(dir_dly3),
        .s_axis_tvalid(win_tvalid), .s_axis_tready(win_tready),
        .s_axis_tuser(win_tuser), .s_axis_tlast(win_tlast),
        .m_axis_tdata(nms_mag), .m_axis_tvalid(nms_tvalid), .m_axis_tready(nms_tready),
        .m_axis_tuser(nms_tuser), .m_axis_tlast(nms_tlast)
    );

    dual_threshold u_th (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_tdata(nms_mag), .s_axis_tvalid(nms_tvalid), .s_axis_tready(nms_tready),
        .s_axis_tuser(nms_tuser), .s_axis_tlast(nms_tlast),
        .m_axis_tdata(th_type), .m_axis_tvalid(th_tvalid), .m_axis_tready(th_tready),
        .m_axis_tuser(th_tuser), .m_axis_tlast(th_tlast),
        .th_high(th_high), .th_low(th_low)
    );

    edge_tracking #(1280) u_edge (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_tdata(th_type), .s_axis_tvalid(th_tvalid), .s_axis_tready(th_tready),
        .s_axis_tuser(th_tuser), .s_axis_tlast(th_tlast),
        .m_axis_tdata(edge_pix), .m_axis_tvalid(edge_tvalid), .m_axis_tready(edge_tready),
        .m_axis_tuser(edge_tuser), .m_axis_tlast(edge_tlast)
    );

    rle_encoder u_rle (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_tdata(edge_pix), .s_axis_tvalid(edge_tvalid), .s_axis_tready(edge_tready),
        .s_axis_tuser(edge_tuser), .s_axis_tlast(edge_tlast),
        .m_axis_tdata(m_axis_rle_tdata), .m_axis_tvalid(m_axis_rle_tvalid),
        .m_axis_tready(m_axis_rle_tready),
        .m_axis_tuser(m_axis_rle_tuser), .m_axis_tlast(m_axis_rle_tlast)
    );

endmodule