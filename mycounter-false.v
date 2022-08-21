module mycounter(input clk,output reg[31:0] cnt);
    initial cnt = 0;
    always@(posedge clk) begin
        if (cnt==3)
            cnt <= 0;
        else
            cnt <= cnt + 1;
    end
    `ifdef FORMAL
        always @(posedge clk) begin
        assert(cnt < 3);
        end
    `endif

endmodule
