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

    wire [1:0] mosi_cmd  = spi_rx_data[7:6];
    wire       mosi_done = spi_rx_data[5];
    wire [4:0] mosi_data = spi_rx_data[4:0];

    localparam CMD_MOSI_NOP   = 2'b00;
    localparam CMD_MOSI_DATA  = 2'b01;
    localparam CMD_MOSI_START = 2'b10;
    localparam CMD_MOSI_RESET = 2'b11;

    localparam CMD_MISO_WAIT = 2'b00;
    localparam CMD_MISO_DATA = 2'b01;
    localparam CMD_MISO_DONE = 2'b11;

    localparam MISO_NOT_EOL = 1'b0;
    localparam MISO_EOL     = 1'b1;

    localparam ST_INIT  = 2'b00;
    localparam ST_INPUT = 2'b01;
    localparam ST_REPLY = 2'b10;
    localparam ST_DONE  = 2'b11;

    reg [1:0] state;

    localparam REPLY_START1 = 2'b00;
    localparam REPLY_START2 = 2'b01;
    localparam REPLY_COUNT  = 2'b10;
    localparam REPLY_MEMBER = 2'b11;

    reg [1:0] reply_phase;

    reg spi_rx_valid_d;

    // Test N:
    // N = 20
    // Final target size for this array-based version.

    integer idx;

    reg [4:0] giver_idx;
    reg       input_closed;

    reg [19:0] hit_bits  [0:19];
    reg [4:0]  hit_count [0:19];

    reg [4:0] reply_receiver;
    reg [4:0] reply_sender;
    reg [4:0] reply_sent_cnt;

    wire recipient_valid =
        (!input_closed) &&
        (giver_idx < 5'd20) &&
        (mosi_data > 5'd0) &&
        (mosi_data <= 5'd20);

    wire [19:0] giver_mask =
        (giver_idx < 5'd20) ? (20'd1 << giver_idx) : 20'd0;

    wire [19:0] current_hit_bits =
        (reply_receiver < 5'd20) ? hit_bits[reply_receiver] : 20'd0;

    wire [4:0] current_hit_count =
        (reply_receiver < 5'd20) ? hit_count[reply_receiver] : 5'd0;

    wire [19:0] reply_sender_mask =
        (reply_sender < 5'd20) ? (20'd1 << reply_sender) : 20'd0;

    wire reply_hit =
        ((current_hit_bits & reply_sender_mask) != 20'd0);

    wire reply_eol =
        ((reply_sent_cnt + 5'd1) == current_hit_count);

    wire reply_not_eol =
        ((reply_sent_cnt + 5'd1) < current_hit_count);

    wire reply_last_receiver =
        (reply_receiver == 5'd19);

    wire [4:0] reply_sender_id =
        reply_sender + 5'd1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_rx_valid_d <= 1'b0;

            state          <= ST_INIT;
            reply_phase    <= REPLY_START1;
            spi_tx_data    <= {CMD_MISO_WAIT, MISO_NOT_EOL, 5'd0};

            giver_idx      <= 5'd0;
            input_closed   <= 1'b0;

            for (idx = 0; idx < 20; idx = idx + 1) begin
                hit_bits[idx]  <= 20'd0;
                hit_count[idx] <= 5'd0;
            end

            reply_receiver <= 5'd0;
            reply_sender   <= 5'd0;
            reply_sent_cnt <= 5'd0;

        end else begin
            spi_rx_valid_d <= spi_rx_valid;

            if (spi_rx_valid && !spi_rx_valid_d) begin
                case (state)

                    ST_INIT: begin
                        spi_tx_data    <= {CMD_MISO_WAIT, MISO_NOT_EOL, 5'd0};

                        giver_idx      <= 5'd0;
                        input_closed   <= 1'b0;

                        for (idx = 0; idx < 20; idx = idx + 1) begin
                            hit_bits[idx]  <= 20'd0;
                            hit_count[idx] <= 5'd0;
                        end

                        reply_receiver <= 5'd0;
                        reply_sender   <= 5'd0;
                        reply_sent_cnt <= 5'd0;
                        reply_phase    <= REPLY_START1;

                        state          <= ST_INPUT;
                    end

                    ST_INPUT: begin
                        if (mosi_cmd == CMD_MOSI_RESET) begin
                            state <= ST_INIT;

                        end else if (mosi_cmd == CMD_MOSI_DATA) begin
                            if (recipient_valid) begin
                                for (idx = 0; idx < 20; idx = idx + 1) begin
                                    if ({27'd0, mosi_data} == idx + 32'd1) begin
                                        if ((hit_bits[idx] & giver_mask) == 20'd0) begin
                                            hit_bits[idx]  <= hit_bits[idx] | giver_mask;
                                            hit_count[idx] <= hit_count[idx] + 5'd1;
                                        end
                                    end
                                end
                            end

                        end else if (mosi_cmd == CMD_MOSI_START) begin
                            input_closed   <= 1'b1;

                            reply_receiver <= 5'd0;
                            reply_sender   <= 5'd0;
                            reply_sent_cnt <= 5'd0;
                            reply_phase    <= REPLY_START1;

                            state          <= ST_REPLY;

                        end else begin
                            spi_tx_data <= {CMD_MISO_WAIT, MISO_NOT_EOL, 5'd0};
                        end

                        if (mosi_done && (mosi_cmd == CMD_MOSI_DATA)) begin
                            if (giver_idx < 5'd19) begin
                                giver_idx <= giver_idx + 5'd1;
                            end else begin
                                input_closed <= 1'b1;
                            end
                        end
                    end

                    ST_REPLY: begin
                        if (mosi_cmd == CMD_MOSI_RESET) begin
                            state <= ST_INIT;

                        end else if (mosi_cmd == CMD_MOSI_NOP) begin
                            case (reply_phase)

                                REPLY_START1: begin
                                    spi_tx_data <= {CMD_MISO_WAIT, MISO_NOT_EOL, 5'd0};
                                    reply_phase <= REPLY_START2;
                                end

                                REPLY_START2: begin
                                    reply_phase <= REPLY_COUNT;
                                end

                                REPLY_COUNT: begin
                                    if (current_hit_count == 5'd0) begin
                                        if (reply_last_receiver) begin
                                            spi_tx_data <= {CMD_MISO_DATA, MISO_EOL, 5'd0};
                                            state       <= ST_DONE;

                                        end else begin
                                            spi_tx_data    <= {CMD_MISO_DATA, MISO_EOL, 5'd0};
                                            reply_receiver <= reply_receiver + 5'd1;
                                            reply_phase    <= REPLY_COUNT;
                                        end

                                    end else begin
                                        spi_tx_data    <= {CMD_MISO_DATA, MISO_NOT_EOL, current_hit_count};
                                        reply_sender   <= 5'd0;
                                        reply_sent_cnt <= 5'd0;
                                        reply_phase    <= REPLY_MEMBER;
                                    end
                                end

                                REPLY_MEMBER: begin
                                    if (reply_hit) begin
                                        if (reply_eol && reply_last_receiver) begin
                                            spi_tx_data <= {CMD_MISO_DATA, MISO_EOL, reply_sender_id};
                                            state       <= ST_DONE;

                                        end else if (reply_eol) begin
                                            spi_tx_data    <= {CMD_MISO_DATA, MISO_EOL, reply_sender_id};
                                            reply_receiver <= reply_receiver + 5'd1;
                                            reply_phase    <= REPLY_COUNT;

                                        end else if (reply_not_eol) begin
                                            spi_tx_data    <= {CMD_MISO_DATA, MISO_NOT_EOL, reply_sender_id};
                                            reply_sender   <= reply_sender + 5'd1;
                                            reply_sent_cnt <= reply_sent_cnt + 5'd1;
                                        end

                                    end else begin
                                        spi_tx_data  <= {CMD_MISO_WAIT, MISO_NOT_EOL, 5'd0};
                                        reply_sender <= reply_sender + 5'd1;
                                    end
                                end

                                default: begin
                                    reply_phase <= REPLY_START1;
                                end
                            endcase
                        end
                    end

                    ST_DONE: begin
                        if (mosi_cmd == CMD_MOSI_RESET) begin
                            state <= ST_INIT;
                        end else begin
                            spi_tx_data <= {CMD_MISO_DONE, MISO_NOT_EOL, 5'd0};
                        end
                    end

                    default: begin
                        state <= ST_INIT;
                    end
                endcase
            end
        end
    end

endmodule