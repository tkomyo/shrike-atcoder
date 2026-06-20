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
    //   [5:0] data
    //
    // cmd:
    //   00 : NOP for readback
    //   01 : Send CHAR   data[4:0] = 0..25  // 'a'..'z'
    //   10 : EOL
    //   11 : reset
    
    // SPI MISO readback status format:
    //   [7:6] status bits
    //   [5:0] data
    //
    // status:
    //   00 : header 'o' section
    //   01 : body section
    //   10 : EOL
    //   11 : reserved
    

    localparam CMD_NOP       = 2'b00; // NOP during readback period
    localparam CMD_SET_CHAR  = 2'b01; // sending char data
    localparam CMD_EOL       = 2'b10; // finished sending char data
    localparam CMD_RESET	 = 2'b11; // reset registers

    wire [1:0] cmd  = spi_rx_data[7:6];
    wire [4:0] data = spi_rx_data[4:0];

    // Logic to handle SPI Commands
    reg spi_rx_valid_d;

    // Define status registers
    reg       eol_reg;
    reg       body_reg;
    reg [4:0] char_reg;
    

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_rx_valid_d <= 1'b0;
            eol_reg        <= 1'd0; // Initialize EOL reg
            body_reg       <= 1'd0; // Initialize Body reg (Beyond 'o' header section)
            char_reg       <= 5'd0; // Initialize char reg
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
    					char_reg <= data;

    					if (eol_reg) begin
        					// Already finished
        					spi_tx_data <= {2'b10, 6'd0};
							
    					end else if (body_reg || data != 5'd14) begin
        					// First non-'o' char, or already in body section
        					body_reg    <= 1'b1;
        					spi_tx_data <= {2'b01, 1'b0, data};
						
    					end else begin
        					// Leading 'o' char: drop it
        					spi_tx_data <= {2'b00, 6'd0};
    					end
					end

					CMD_EOL: begin
    					eol_reg     <= 1'b1;
    					spi_tx_data <= {2'b10, 6'd0};
					end
                    
                    CMD_RESET: begin
            			eol_reg        <= 1'd0; // Initialize EOL reg
            			body_reg       <= 1'd0; // Initialize Body reg (Beyond 'o' header section)
            			char_reg       <= 5'd0; // Initialize char reg
            			spi_tx_data    <= 8'd0; // Initialize readback data                    
                    end                    
                endcase
            end
        end
    end

endmodule
