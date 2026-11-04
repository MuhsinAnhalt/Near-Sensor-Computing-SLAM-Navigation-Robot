# =====================================================================
# 1. 电机控制与编码器 (Pmod 接口, Bank 45) - 统一 3.3V
# =====================================================================
set_property PACKAGE_PIN H12 [get_ports pwm_l_out]
set_property IOSTANDARD LVCMOS33 [get_ports pwm_l_out]

set_property PACKAGE_PIN E10 [get_ports pwm_r_out]
set_property IOSTANDARD LVCMOS33 [get_ports pwm_r_out]

set_property PACKAGE_PIN D10 [get_ports dir_l_out]
set_property IOSTANDARD LVCMOS33 [get_ports dir_l_out]

set_property PACKAGE_PIN C11 [get_ports dir_r_out]
set_property IOSTANDARD LVCMOS33 [get_ports dir_r_out]

set_property PACKAGE_PIN B10 [get_ports enc_a_l]
set_property IOSTANDARD LVCMOS33 [get_ports enc_a_l]

set_property PACKAGE_PIN E12 [get_ports enc_b_l]
set_property IOSTANDARD LVCMOS33 [get_ports enc_b_l]

set_property PACKAGE_PIN D11 [get_ports enc_a_r]
set_property IOSTANDARD LVCMOS33 [get_ports enc_a_r]

set_property PACKAGE_PIN B11 [get_ports enc_b_r]
set_property IOSTANDARD LVCMOS33 [get_ports enc_b_r]

# =====================================================================
# 2. 摄像头使能与 I2C (J9 接口, Bank 45)
# =====================================================================
# F11 摄像头使能 (PS EMIO 或 PL GPIO)
set_property PACKAGE_PIN F11 [get_ports {GPIO_0_0_tri_io[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {GPIO_0_0_tri_io[0]}]

set_property PACKAGE_PIN F10 [get_ports GPIO_0_tri_io[0]]
set_property PACKAGE_PIN G11 [get_ports GPIO_0_tri_io[1]]
set_property IOSTANDARD LVCMOS33 [get_ports GPIO_0_tri_io[*]]



# 注意：之前 G10 的 cam_mclk 约束已经被彻底删除了（因为模组有晶振）

# =====================================================================
# 3. MIPI D-PHY 差分对约束 (J9, Bank 66)
# =====================================================================
# MIPI Clock Lane
set_property PACKAGE_PIN G1 [get_ports mipi_phy_if_0_clk_p]
set_property PACKAGE_PIN H2 [get_ports mipi_phy_if_0_clk_n]
set_property IOSTANDARD MIPI_DPHY_DCI [get_ports {mipi_phy_if_0_clk_p mipi_phy_if_0_clk_n}]
set_property DIFF_TERM_ADV TERM_100 [get_ports {mipi_phy_if_0_clk_p mipi_phy_if_0_clk_n}]

# MIPI Data Lane 0
set_property PACKAGE_PIN E1 [get_ports {mipi_phy_if_0_data_p[0]}]
set_property PACKAGE_PIN E2 [get_ports {mipi_phy_if_0_data_n[0]}]
set_property IOSTANDARD MIPI_DPHY_DCI [get_ports {mipi_phy_if_0_data_p[0] mipi_phy_if_0_data_n[0]}]
set_property DIFF_TERM_ADV TERM_100 [get_ports {mipi_phy_if_0_data_p[0] mipi_phy_if_0_data_n[0]}]

# MIPI Data Lane 1
set_property PACKAGE_PIN F2 [get_ports {mipi_phy_if_0_data_p[1]}]
set_property PACKAGE_PIN F1 [get_ports {mipi_phy_if_0_data_n[1]}]
set_property IOSTANDARD MIPI_DPHY_DCI [get_ports {mipi_phy_if_0_data_p[1] mipi_phy_if_0_data_n[1]}]
set_property DIFF_TERM_ADV TERM_100 [get_ports {mipi_phy_if_0_data_p[1] mipi_phy_if_0_data_n[1]}]