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
    wire       spi_rx_valid;
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

    // MOSI command format
    // [7:6] : command
    // [5]   : EOL / DONE flag
    // [4:0] : data

    wire [1:0] mosi_cmd  = spi_rx_data[7:6];
    wire       mosi_done = spi_rx_data[5];
    wire [4:0] mosi_data = spi_rx_data[4:0];

    // MISO format
    // [7:6] : status
    // [5]   : EOL flag
    // [4:0] : data

    localparam CMD_MOSI_NOP   = 2'b00;
    localparam CMD_MOSI_DATA  = 2'b01;
    localparam CMD_MOSI_START = 2'b10;
    localparam CMD_MOSI_RESET = 2'b11;

    localparam CMD_MISO_WAIT = 2'b00;
    localparam CMD_MISO_DATA = 2'b01;
    localparam CMD_MISO_DONE = 2'b11;

    localparam MISO_NOT_EOL = 1'b0;
    localparam MISO_EOL     = 1'b1;

    // Top-level FSM
    localparam ST_INIT  = 2'b00;
    localparam ST_INPUT = 2'b01;
    localparam ST_REPLY = 2'b10;
    localparam ST_DONE  = 2'b11;

    reg [1:0] state;

    // Reply sub FSM
    localparam REPLY_START1 = 2'b00;
    localparam REPLY_START2 = 2'b01;
    localparam REPLY_COUNT  = 2'b10;
    localparam REPLY_MEMBER = 2'b11;

    reg [1:0] reply_phase;

    // Edge detect for spi_rx_valid
    reg spi_rx_valid_d;

    // Test I:
    // N = 5
    // Use multiple unpacked arrays.
    // This test checks whether hit_bits[0:4] and hit_count[0:4] are acceptable
    // inside the FSM structure.

    integer idx;

    reg [4:0] giver_idx;
    reg       input_closed;

    reg [4:0] hit_bits  [0:4];
    reg [2:0] hit_count [0:4];

    reg [2:0] reply_receiver;
    reg [2:0] reply_sender;
    reg [2:0] reply_sent_cnt;

    wire recipient_valid =
        (!input_closed) &&
        (giver_idx < 5'd5) &&
        (mosi_data > 5'd0) &&
        (mosi_data <= 5'd5);

    wire [4:0] giver_mask =
        (giver_idx < 5'd5) ? (5'd1 << giver_idx) : 5'd0;

    wire [4:0] current_hit_bits =
        (reply_receiver < 3'd5) ? hit_bits[reply_receiver] : 5'd0;

    wire [2:0] current_hit_count =
        (reply_receiver < 3'd5) ? hit_count[reply_receiver] : 3'd0;

    wire [4:0] reply_sender_mask =
        (reply_sender < 3'd5) ? (5'd1 << reply_sender) : 5'd0;

    wire reply_hit =
        ((current_hit_bits & reply_sender_mask) != 5'd0);

    wire reply_eol =
        ((reply_sent_cnt + 3'd1) == current_hit_count);

    wire reply_not_eol =
        ((reply_sent_cnt + 3'd1) < current_hit_count);

    wire reply_last_receiver =
        (reply_receiver == 3'd4);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_rx_valid_d <= 1'b0;

            state          <= ST_INIT;
            reply_phase    <= REPLY_START1;
            spi_tx_data    <= {CMD_MISO_WAIT, MISO_NOT_EOL, 5'd0};

            giver_idx      <= 5'd0;
            input_closed   <= 1'b0;

            for (idx = 0; idx < 5; idx = idx + 1) begin
                hit_bits[idx]  <= 5'd0;
                hit_count[idx] <= 3'd0;
            end

            reply_receiver <= 3'd0;
            reply_sender   <= 3'd0;
            reply_sent_cnt <= 3'd0;

        end else begin
            spi_rx_valid_d <= spi_rx_valid;

            if (spi_rx_valid && !spi_rx_valid_d) begin
                case (state)

                    ST_INIT: begin

//                      ST_INIT:
//                          SET SPI_TX as WAIT with NOT_EOL
//                          SET GIVER_IDX as 0
//                          CLEAR INPUT_CLOSED
//                          CLEAR HIT_BITS[0..4]
//                          CLEAR HIT_COUNT[0..4]
//                          SET REPLY_RECEIVER as 0
//                          SET REPLY_SENDER as 0
//                          SET REPLY_SENT_CNT as 0
//                          SET REPLY_PHASE as REPLY_START1
//                          SET STATE as ST_INPUT
//
//                      ---- Related regs ----
//                      spi_tx_data    : reg [7:0] : SPI msg byte from FPGA to RP2040
//                      giver_idx      : reg [4:0] : current gift giver index, 0..4
//                      input_closed   : reg       : input completion flag
//                      hit_bits       : reg [4:0] [0:4] : sender bitset for each receiver
//                      hit_count      : reg [2:0] [0:4] : sender count for each receiver
//                      reply_receiver : reg [2:0] : current receiver index, 0..4
//                      reply_sender   : reg [2:0] : current sender index, 0..4
//                      reply_sent_cnt : reg [2:0] : count of sender IDs already output
//                      reply_phase    : reg [1:0] : reply sub FSM state
//                      state          : reg [1:0] : top-level FSM state

                        spi_tx_data    <= {CMD_MISO_WAIT, MISO_NOT_EOL, 5'd0};

                        giver_idx      <= 5'd0;
                        input_closed   <= 1'b0;

                        for (idx = 0; idx < 5; idx = idx + 1) begin
                            hit_bits[idx]  <= 5'd0;
                            hit_count[idx] <= 3'd0;
                        end

                        reply_receiver <= 3'd0;
                        reply_sender   <= 3'd0;
                        reply_sent_cnt <= 3'd0;
                        reply_phase    <= REPLY_START1;

                        state          <= ST_INPUT;
                    end

                    ST_INPUT: begin

//                      ST_INPUT:
//                          if (MOSI_RESET) begin
//                              SET STATE as ST_INIT
//                          end else if (MOSI_DATA) begin
//                              if (RECIPIENT_VALID) begin
//                                  SET HIT_BITS[RECEIVER] as HIT_BITS[RECEIVER] | GIVER_MASK
//                                  SET HIT_COUNT[RECEIVER] as HIT_COUNT[RECEIVER] + 1
//                              end
//                          end else if (MOSI_START) begin
//                              SET INPUT_CLOSED as 1
//                              SET REPLY_RECEIVER as 0
//                              SET REPLY_SENDER as 0
//                              SET REPLY_SENT_CNT as 0
//                              SET REPLY_PHASE as REPLY_START1
//                              SET STATE as ST_REPLY
//                          end else begin
//                              SET SPI_TX as WAIT with NOT_EOL
//                          end
//
//                      NOTE:
//                          Test I uses multiple unpacked arrays.
//                          Write side uses fixed idx loop.
//                          Read side uses reply_receiver indexed array access.

                        if (mosi_cmd == CMD_MOSI_RESET) begin
                            state <= ST_INIT;

                        end else if (mosi_cmd == CMD_MOSI_DATA) begin
                            if (recipient_valid) begin
                                for (idx = 0; idx < 5; idx = idx + 1) begin
                                    if ({27'd0, mosi_data} == idx + 32'd1) begin
                                        if ((hit_bits[idx] & giver_mask) == 5'd0) begin
                                            hit_bits[idx]  <= hit_bits[idx] | giver_mask;
                                            hit_count[idx] <= hit_count[idx] + 3'd1;
                                        end
                                    end
                                end
                            end

                        end else if (mosi_cmd == CMD_MOSI_START) begin
                            input_closed   <= 1'b1;

                            reply_receiver <= 3'd0;
                            reply_sender   <= 3'd0;
                            reply_sent_cnt <= 3'd0;
                            reply_phase    <= REPLY_START1;

                            state          <= ST_REPLY;

                        end else begin
                            spi_tx_data <= {CMD_MISO_WAIT, MISO_NOT_EOL, 5'd0};
                        end

                        if (mosi_done && (mosi_cmd == CMD_MOSI_DATA)) begin
                            if (giver_idx < 5'd4) begin
                                giver_idx <= giver_idx + 5'd1;
                            end else begin
                                input_closed <= 1'b1;
                            end
                        end
                    end

                    ST_REPLY: begin

//                      ST_REPLY:
//                          if (MOSI_RESET) begin
//                              SET STATE as ST_INIT
//                          end else if (MOSI_NOP) begin
//                              RUN REPLY_PHASE
//                          end
//
//                      REPLY_START1:
//                          SET SPI_TX as WAIT with NOT_EOL
//                          SET REPLY_PHASE as REPLY_START2
//
//                      REPLY_START2:
//                          SET REPLY_PHASE as REPLY_COUNT
//
//                      REPLY_COUNT:
//                          if (CURRENT_HIT_COUNT == 0) begin
//                              if (REPLY_LAST_RECEIVER) begin
//                                  SET SPI_TX as DATA with EOL and 0
//                                  SET STATE as ST_DONE
//                              end else begin
//                                  SET SPI_TX as DATA with EOL and 0
//                                  SET REPLY_RECEIVER as REPLY_RECEIVER + 1
//                                  SET REPLY_PHASE as REPLY_COUNT
//                              end
//                          end else begin
//                              SET SPI_TX as DATA with NOT_EOL and CURRENT_HIT_COUNT
//                              SET REPLY_SENDER as 0
//                              SET REPLY_SENT_CNT as 0
//                              SET REPLY_PHASE as REPLY_MEMBER
//                          end
//
//                      REPLY_MEMBER:
//                          if (REPLY_HIT) begin
//                              if (REPLY_EOL && REPLY_LAST_RECEIVER) begin
//                                  SET SPI_TX as DATA with EOL and SENDER_ID
//                                  SET STATE as ST_DONE
//                              end else if (REPLY_EOL) begin
//                                  SET SPI_TX as DATA with EOL and SENDER_ID
//                                  SET REPLY_RECEIVER as REPLY_RECEIVER + 1
//                                  SET REPLY_PHASE as REPLY_COUNT
//                              end else if (REPLY_NOT_EOL) begin
//                                  SET SPI_TX as DATA with NOT_EOL and SENDER_ID
//                                  SET REPLY_SENDER as REPLY_SENDER + 1
//                                  SET REPLY_SENT_CNT as REPLY_SENT_CNT + 1
//                              end
//                          end else begin
//                              SET SPI_TX as WAIT with NOT_EOL
//                              SET REPLY_SENDER as REPLY_SENDER + 1
//                          end
//
//                      ---- Related wires ----
//                      current_hit_bits   : wire [4:0] : hit_bits[reply_receiver]
//                      current_hit_count  : wire [2:0] : hit_count[reply_receiver]
//                      reply_sender_mask  : wire [4:0] : one-hot mask for reply_sender
//                      reply_hit          : wire       : TRUE if current sender is included
//                      reply_eol          : wire       : TRUE if current sender is last output member
//                      reply_not_eol      : wire       : TRUE if more output members remain
//                      reply_last_receiver: wire       : TRUE if reply_receiver == 4

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
                                    if (current_hit_count == 3'd0) begin
                                        if (reply_last_receiver) begin
                                            spi_tx_data <= {CMD_MISO_DATA, MISO_EOL, 5'd0};
                                            state       <= ST_DONE;

                                        end else begin
                                            spi_tx_data    <= {CMD_MISO_DATA, MISO_EOL, 5'd0};
                                            reply_receiver <= reply_receiver + 3'd1;
                                            reply_phase    <= REPLY_COUNT;
                                        end

                                    end else begin
                                        spi_tx_data    <= {CMD_MISO_DATA, MISO_NOT_EOL, 2'b00, current_hit_count};
                                        reply_sender   <= 3'd0;
                                        reply_sent_cnt <= 3'd0;
                                        reply_phase    <= REPLY_MEMBER;
                                    end
                                end

                                REPLY_MEMBER: begin
                                    if (reply_hit) begin
                                        if (reply_eol && reply_last_receiver) begin
                                            spi_tx_data <= {CMD_MISO_DATA, MISO_EOL, 2'b00, reply_sender + 3'd1};
                                            state       <= ST_DONE;

                                        end else if (reply_eol) begin
                                            spi_tx_data    <= {CMD_MISO_DATA, MISO_EOL, 2'b00, reply_sender + 3'd1};
                                            reply_receiver <= reply_receiver + 3'd1;
                                            reply_phase    <= REPLY_COUNT;

                                        end else if (reply_not_eol) begin
                                            spi_tx_data    <= {CMD_MISO_DATA, MISO_NOT_EOL, 2'b00, reply_sender + 3'd1};
                                            reply_sender   <= reply_sender + 3'd1;
                                            reply_sent_cnt <= reply_sent_cnt + 3'd1;
                                        end

                                    end else begin
                                        spi_tx_data  <= {CMD_MISO_WAIT, MISO_NOT_EOL, 5'd0};
                                        reply_sender <= reply_sender + 3'd1;
                                    end
                                end

                                default: begin
                                    reply_phase <= REPLY_START1;
                                end
                            endcase
                        end
                    end

                    ST_DONE: begin

//                      ST_DONE:
//                          if (MOSI_RESET) begin
//                              SET STATE as ST_INIT
//                          end else begin
//                              SET SPI_TX as DONE with NOT_EOL
//                          end

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