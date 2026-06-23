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
    
    // FSM state
    reg state;
    
    localparam ST_IDLE     = 1'b0;
    localparam ST_WAIT_LOW = 1'b1;
    
    // 1st rx byte
    reg [2:0] pending_cmd;
    reg [2:0] pending_aux;
    reg [1:0] pending_data;
    
    localparam CMD_NOP   = 3'b000;
    localparam CMD_SET_X = 3'b001;
    localparam CMD_SET_Y = 3'b010;
    localparam CMD_DEBUG = 3'b101;
    localparam CMD_RESET = 3'b111;
    
    // reg & wire for x, y, result
    reg [13:0] x_reg;

    wire [13:0] y_data14;
    assign y_data14 = {4'd0, pending_data, spi_rx_data};
    
    wire reply_result;
    assign reply_result = ((x_reg << 3) + x_reg) == (y_data14 << 4);
    
    
    // reply enable flags
    reg reply_ready;
    
	
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_rx_valid_d <= 1'b0;
            state		   <= ST_IDLE;
            pending_cmd	   <= 3'd0;
            pending_aux    <= 3'd0;
            pending_data   <= 2'b0;
            x_reg		   <= 14'd0;
            reply_ready	   <= 1'b0;
            spi_tx_data    <= 8'd0;
            
        end else begin
            spi_rx_valid_d <= spi_rx_valid;            

            // Detect rising edge of spi_rx_valid
            if (spi_rx_valid && !spi_rx_valid_d) begin
                
                case (state)
                	ST_IDLE: begin
						pending_cmd  <= spi_rx_data [7:5];
						pending_aux  <= spi_rx_data [4:2];
						pending_data <= spi_rx_data [1:0];
						state		 <= ST_WAIT_LOW;                		
                	end
                	
                	ST_WAIT_LOW: begin
                	
                		case (pending_cmd)
                			CMD_NOP: begin
								if (reply_ready == 1'b1) begin
									spi_tx_data <= 8'd0;
									reply_ready <= 1'b0;
								end
								state <= ST_IDLE;
                			end
                			
                			CMD_SET_X: begin
								x_reg <= {4'd0, pending_data, spi_rx_data};
								state		 <= ST_IDLE;
                			end
                			
                			CMD_SET_Y: begin
                				spi_tx_data <= {1'b1, 6'd0, reply_result};
                				reply_ready <= 1'b1;
								state		<= ST_IDLE;
                    		end
                    		
                    		CMD_DEBUG: begin
                    			state <= ST_IDLE;
                    			// No operation is implemented so far
                    		end
                    		
                    		CMD_RESET: begin
            					state		   <= ST_IDLE;
            					pending_cmd	   <= 3'd0;
            					pending_aux    <= 3'd0;
            					pending_data   <= 2'b0;
            					x_reg		   <= 14'd0;
            					reply_ready	   <= 1'b0;
            					spi_tx_data    <= 8'd0;
                    		end
                    		
                    		default: begin
                    			state <= ST_IDLE;
                    			// No operation for undefined command
                    		end
                		endcase
                	end
                	
					default: begin
						state <= ST_IDLE;
						// No operation for undefined command
					end
                endcase
            end
        end
    end

endmodule
