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

    // Wires for SPI module
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

    // Logic to handle SPI commands
    reg spi_rx_valid_d;
    
    wire [2:0] mosi_cmd;
    assign mosi_cmd = spi_rx_data [7:5];
    
    localparam CMD_NOP   = 3'b000;
    localparam CMD_DATA  = 3'b001;
    localparam CMD_EOD   = 3'b010;
    localparam CMD_DEBUG = 3'b101;
    localparam CMD_RESET = 3'b111;
    
    wire mosi_bit;
    assign mosi_bit = spi_rx_data[0];

    reg signed [7:0] diff;
    reg [7:0] reply_reg;

    assign spi_tx_data = reply_reg;
    
	
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_rx_valid_d <= 1'b0;
            reply_reg      <= 8'h00;
            diff           <= 8'sd0;
            
        end else begin
            spi_rx_valid_d <= spi_rx_valid;            

            // Detect rising edge of spi_rx_valid
            if (spi_rx_valid && !spi_rx_valid_d) begin
                
                case (mosi_cmd)
                	CMD_NOP: begin
                		// Keep current reply_reg for readback.
                	end
                	
                	CMD_DATA: begin
                		if (mosi_bit) begin
                			diff <= diff + 8'sd1;
                		end else begin
                			diff <= diff - 8'sd1;
                		end
                	end
                	
                	CMD_EOD: begin
                		if (diff > 8'sd0) begin
                			reply_reg <= 8'h81;
                		end else begin
                			reply_reg <= 8'h80;
                		end
                	end
                	
                	CMD_DEBUG: begin
                		reply_reg <= diff[7:0];
                	end
                	
                	CMD_RESET: begin
            			reply_reg   <= 8'h00;
            			diff        <= 8'sd0;
                	end
                	
                	default: begin
                		// No operation for undefined command.
                	end
                endcase
            end
        end
    end

endmodule
