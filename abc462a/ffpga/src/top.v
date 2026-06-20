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
    reg  [7:0] spi_tx_data;

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

    // SPI MOSI command format:
    //   [7:6] cmd
    //	 [5]   nibble
    //	 [4]   unused
    //   [3:0] data
    //
    // cmd:
    //   00 : NOP for readback
    //   01 : Send CHAR data   data[3:0]
    //   10 : EOL
    //   11 : reset
    //
    // nibble:
    //   0 : send upper nibble
    //   1 : send lower nibble
    //
    // SPI MOSI sequence:
    //   reset -> send upper nibble -> send lower nibble -> NOP readback -> EOL
    
    // SPI MISO readback status format:
    //   [7:6] status bits
    //   [5:4] unused
    //   [3:0] digit data: uint_4 (0-15)
    //
    // status:
    //   00 : no output / output should be ignored
    //   01 : digit output
    //   10 : EOL
    //   11 : reserved
    

    localparam CMD_NOP       = 2'b00; // NOP during readback period
    localparam CMD_SET_CHAR  = 2'b01; // sending char data
    localparam CMD_EOL       = 2'b10; // finished sending char data
    localparam CMD_RESET	 = 2'b11; // reset registers
    
    localparam NIBBLE_LOWER  = 1'b1;  // 0 = Upper Nibble, 1 = Lower Nibble

    wire [1:0] cmd    = spi_rx_data[7:6];
    wire	   nibble = spi_rx_data[5];
    wire [3:0] data   = spi_rx_data[3:0];

    // Logic to handle SPI Commands
    reg spi_rx_valid_d;

    // Define status registers
    reg       eol_reg;
    reg [3:0] upper_data_reg;
    
    // Define char data wire
    wire [7:0] ascii_data = {upper_data_reg, data};
    

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_rx_valid_d <= 1'b0;
            eol_reg        <= 1'd0; // Initialize EOL reg
            upper_data_reg <= 4'd0; // Initialize char reg
            spi_tx_data    <= 8'd0; // Initialize readback data
        end else begin
            spi_rx_valid_d <= spi_rx_valid;

            // Detect rising edge of spi_rx_valid
            if (spi_rx_valid && !spi_rx_valid_d) begin
                case (cmd)
                    CMD_NOP: begin
            			spi_tx_data    <= 8'd0; // Refresh readback data                    
                    end
					
					CMD_SET_CHAR: begin
    					if (eol_reg) begin
        					// Already finished
        					spi_tx_data 	<= {2'b10, 6'd0};
							
    					end else if (!nibble) begin
        					// Upper nibble RX
        					upper_data_reg	<= data;
						
    					end else begin
        					// Lower nibble RX
        					if (ascii_data >= 8'h30 && ascii_data <= 8'h39) begin
        						spi_tx_data <= {4'b0100, data};
        					end else begin
        						spi_tx_data <= 8'd0;
        					end
    					end
					end

					CMD_EOL: begin
    					eol_reg     <= 1'b1;
    					spi_tx_data <= {2'b10, 6'd0};
					end
                    
                    CMD_RESET: begin
            			eol_reg        <= 1'd0; // Initialize EOL reg
            			upper_data_reg <= 4'd0; // Initialize Upper nibble reg
            			spi_tx_data    <= 8'd0; // Initialize readback data                    
                    end                    
                endcase
            end
        end
    end

endmodule
