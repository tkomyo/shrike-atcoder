(* top *) module top (
    (* iopad_external_pin, clkbuf_inhibit *) input clk,
    (* iopad_external_pin *) output clk_en,
    (* iopad_external_pin *) input rst_n,
  
    (* iopad_external_pin *) input spi_ss_n,   
    (* iopad_external_pin *) input spi_sck,    
    (* iopad_external_pin *) input spi_mosi,   
    (* iopad_external_pin *) output spi_miso,  
    (* iopad_external_pin *) output spi_miso_en
);

    
    assign clk_en = 1'b1;

    // Wires for SPI Module
    wire [7:0] spi_rx_data;
    wire spi_rx_valid;
    wire [7:0] spi_tx_data;

    // Instantiate SPI Target
    spi_target #( .WIDTH(8) ) u_spi_target (
        .i_clk(clk),
        .i_rst_n(rst_n),
        .i_enable(1'b1),
        .i_ss_n(spi_ss_n),
        .i_sck(spi_sck),
        .i_mosi(spi_mosi),
        .o_miso(spi_miso),
        .o_miso_oe(spi_miso_en),
        .o_rx_data(spi_rx_data),
        .o_rx_data_valid(spi_rx_valid),
        .i_tx_data(spi_tx_data),
        .o_tx_data_hold()
    );

    // SPI command format:
    //   [7:6] cmd
    //   [5:0] data
    //
    // cmd:
    //   00 : NOP / read result
    //   01 : set M
    //   10 : set D
    //   11 : reserved

    localparam CMD_NOP   = 2'b00;
    localparam CMD_SET_M = 2'b01;
    localparam CMD_SET_D = 2'b10;

    wire [1:0] cmd = spi_rx_data[7:6];
    wire [5:0] data = spi_rx_data[5:0];

    // Logic to handle SPI Commands
    reg spi_rx_valid_d;

    // Define Month and Date Registers
    reg [3:0] m_reg;
    reg [4:0] d_reg;

    wire yes;

    assign yes =
        (m_reg == 4'd1 && d_reg == 5'd7) ||
        (m_reg == 4'd3 && d_reg == 5'd3) ||
        (m_reg == 4'd5 && d_reg == 5'd5) ||
        (m_reg == 4'd7 && d_reg == 5'd7) ||
        (m_reg == 4'd9 && d_reg == 5'd9);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_rx_valid_d <= 1'b0;
            m_reg          <= 4'd0; // Zero initiallize to an invalid month
            d_reg          <= 5'd0; // Zero initiallize to an invalid date
        end else begin
            spi_rx_valid_d <= spi_rx_valid;

            // Detect rising edge of spi_rx_valid
            if (spi_rx_valid && !spi_rx_valid_d) begin
                case (cmd)
                    CMD_NOP: ; // No action needed for NOP for read results
                    CMD_SET_M: m_reg <= data[3:0]; // Use lower 4 bits for month
                    CMD_SET_D: d_reg <= data[4:0]; // Use lower 5 bits for date
                    default: ; // No action for NOP or reserved commands
                endcase
            end
        end
    end
    
    // Readback: Always reflects the physical state of the 8 GPIO pins
    assign spi_tx_data = {7'b0000000, yes}; // bit 0 is 'yes', rest are 0;

endmodule
