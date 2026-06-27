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

    // ------------------------------------------------------------
    // SPI module
    // ------------------------------------------------------------

    wire [7:0] spi_rx_data;
    wire       spi_rx_valid;
    reg  [7:0] spi_tx_data;

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

    // ------------------------------------------------------------
    // Test_A:
    //   MOSI 3 bytes -> MISO 2 bytes
    //
    // MOSI frame:
    //   byte0: [7:5] CMD, [4] CMD_AUX, [3:0] IDX
    //   byte1: [7:2] AUX, [1:0] DATA[9:8]
    //   byte2: [7:0] DATA[7:0]
    //
    // Reply:
    //   [15:13] RSP_OK
    //   [12:10] CMD echo
    //   [ 9: 0] DATA echo
    //
    // DATA[9:8] is stored in data_hi_reg.
    // DATA[7:0] is taken from spi_rx_data at byte2.
    // ------------------------------------------------------------

    localparam [2:0] RSP_OK = 3'b010;

    localparam [2:0] ST_RX_B0  = 3'd0;
    localparam [2:0] ST_RX_B1  = 3'd1;
    localparam [2:0] ST_RX_B2  = 3'd2;
    localparam [2:0] ST_TX_HI  = 3'd3;
    localparam [2:0] ST_TX_LO  = 3'd4;

    reg [2:0] state;

    reg       spi_rx_valid_d;

    reg [2:0] cmd_reg;
    reg       cmd_aux_reg;
    reg [3:0] idx_reg;
    reg [5:0] aux_reg;
    reg [1:0] data_hi_reg;

    reg [7:0] reply_lo_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_rx_valid_d <= 1'b0;
            spi_tx_data    <= 8'h00;

            state          <= ST_RX_B0;

            cmd_reg        <= 3'd0;
            cmd_aux_reg    <= 1'b0;
            idx_reg        <= 4'd0;
            aux_reg        <= 6'd0;
            data_hi_reg    <= 2'd0;

            reply_lo_reg   <= 8'h00;

        end else begin
            spi_rx_valid_d <= spi_rx_valid;

            if (spi_rx_valid && !spi_rx_valid_d) begin
                case (state)

                    ST_RX_B0: begin
                        // byte0:
                        // [7:5] CMD
                        // [4]   CMD_AUX
                        // [3:0] IDX
                        cmd_reg     <= spi_rx_data[7:5];
                        cmd_aux_reg <= spi_rx_data[4];
                        idx_reg     <= spi_rx_data[3:0];

                        state       <= ST_RX_B1;
                    end

                    ST_RX_B1: begin
                        // byte1:
                        // [7:2] AUX
                        // [1:0] DATA[9:8]
                        aux_reg     <= spi_rx_data[7:2];
                        data_hi_reg <= spi_rx_data[1:0];

                        state       <= ST_RX_B2;
                    end

                    ST_RX_B2: begin
                        // byte2:
                        // [7:0] DATA[7:0]
                        //
                        // Prepare reply high byte for next SPI byte.
                        //
                        // reply[15:8] =
                        //   RSP_OK[2:0], CMD[2:0], DATA[9:8]
                        //
                        // reply[7:0] =
                        //   DATA[7:0]
                        spi_tx_data  <= {RSP_OK, cmd_reg, data_hi_reg};
                        reply_lo_reg <= spi_rx_data;

                        state        <= ST_TX_HI;
                    end

                    ST_TX_HI: begin
                        // This received byte was dummy for reply high byte.
                        // Prepare reply low byte for next SPI byte.
                        spi_tx_data <= reply_lo_reg;

                        state       <= ST_TX_LO;
                    end

                    ST_TX_LO: begin
                        // This received byte was dummy for reply low byte.
                        // Return to receive next 3-byte MOSI frame.
                        spi_tx_data <= 8'h00;

                        state       <= ST_RX_B0;
                    end

                    default: begin
                        spi_tx_data <= 8'h00;
                        state       <= ST_RX_B0;
                    end
                endcase
            end
        end
    end

endmodule