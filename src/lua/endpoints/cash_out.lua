-- src/lua/endpoints/cash_out.lua

-- ==========================================================================
-- CashOut Endpoint Params
-- ==========================================================================

---@class Request.Endpoint.CashOut.Params

-- ==========================================================================
-- CashOut Endpoint
-- ==========================================================================

---@type Endpoint
return {

  name = "cash_out",

  description = "Cash out and collect round rewards",

  schema = {},

  requires_state = { G.STATES.ROUND_EVAL },

  ---@param _ Request.Endpoint.CashOut.Params
  ---@param send_response fun(response: Response.Endpoint)
  execute = function(_, send_response)
    sendDebugMessage("Init cash_out()", "BB.ENDPOINTS")

    local num_items = function(area)
      local count = 0
      if area and area.cards then
        for _, v in ipairs(area.cards) do
          if v.children.buy_button and v.children.buy_button.definition then
            count = count + 1
          end
        end
      end
      return count
    end

    -- Wait for SHOP state after state transition completes
    local function wait_for_shop()
      G.E_MANAGER:add_event(Event({
        trigger = "condition",
        blocking = false,
        func = function()
          local done = false
          if G.STATE == G.STATES.SHOP and G.STATE_COMPLETE then
            done = num_items(G.shop_booster) > 0 or num_items(G.shop_jokers) > 0 or num_items(G.shop_vouchers) > 0
            if done then
              sendDebugMessage("Return cash_out() - reached SHOP state", "BB.ENDPOINTS")
              send_response(BB_GAMESTATE.get_gamestate())
              return done
            end
          end
          return done
        end,
      }))
    end

    -- Wait until the round evaluation has stored this round's total in
    -- G.GAME.current_round.dollars (the game shows the Cash Out button at the
    -- same moment). G.FUNCS.cash_out pays that value immediately, so calling
    -- it earlier pays the previous round's total.
    G.E_MANAGER:add_event(Event({
      trigger = "condition",
      blocking = false,
      func = function()
        if G.STATE ~= G.STATES.ROUND_EVAL or not BB_GAMESTATE.round_eval_complete() then
          return false
        end
        sendDebugMessage("cash_out() - round evaluation complete, cashing out", "BB.ENDPOINTS")
        G.FUNCS.cash_out({ config = {} })
        wait_for_shop()
        return true
      end,
    }))
  end,
}
