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

    // Logic to handle SPI Commands
    reg spi_rx_valid_d;
    
    // Rx MISO cmd
    wire [2:0] mosi_cmd;
    assign mosi_cmd = spi_rx_data [7:5];
    
    localparam CMD_NOP   = 3'b000;
    localparam CMD_SET_X = 3'b001;
    localparam CMD_SET_S = 3'b010;
    localparam CMD_DEBUG = 3'b101;
    localparam CMD_RESET = 3'b111;
    
    // Rx MISO data
    wire [4:0] mosi_data;
    assign mosi_data = spi_rx_data [4:0];
    
    // X data reg
    reg [4:0] x_reg;
    
    // reply resuly reg
    reg reply_result;
    
	
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_rx_valid_d <= 1'b0;
            spi_tx_data	   <= 8'd0;
            x_reg		   <= 5'b0;
            reply_result   <= 1'b0;
            
        end else begin
            spi_rx_valid_d <= spi_rx_valid;            

            // Detect rising edge of spi_rx_valid
            if (spi_rx_valid && !spi_rx_valid_d) begin
                
                case (mosi_cmd)
                	CMD_NOP: begin
                		// No operation is implemented so far
                	end
                	
                	CMD_SET_X: begin
                		x_reg 	  <= mosi_data;
                	end
                	
                	CMD_SET_S: begin
                		if ((mosi_data & x_reg) != 5'd0) begin
                			spi_tx_data  <= {1'b1, 6'd0, 1'b1};
                			reply_result <= 1'b1;
                		end else begin
                			spi_tx_data <= {1'b1, 6'd0, reply_result};
                		end
                	end
                	
                	CMD_DEBUG: begin
                		// No operation is implemented so far
                	end
                	
                	CMD_RESET: begin
            			spi_tx_data	   <= 8'd0;
            			x_reg		   <= 5'b0;
            			reply_result   <= 1'b0;
                	end
                	
                	default: begin
                		// No operation for undefined command
                	end
                endcase
            end
        end
    end

endmodule
