local directory = assert(debug.getinfo(1,"S").source:match("^@(.+[/\\])"))
package.path = directory .. "?.lua;" .. package.path
local runtime = require("cabin_runtime")
local mod = runtime.start(directory,require("definition"))
require("cabin_host_settings").start(mod)
local speed = require("speed")
local BOARD = "/Game/CabinGameContent/BoardGameStuff/Board/GameBoard_BP.GameBoard_BP_C"
local SPEED_EVENT = BOARD .. ":CabinFastTurnsSpeed_MC"
local CARD = "/Game/CabinGameContent/BoardGameStuff/Cards/ParentCard.ParentCard_C"
local THIEF = "/Game/CabinGameContent/BoardGameStuff/Cards/ChanceCards/PC_Thief.PC_Thief_C"
local CATCHING_UP = "/Game/CabinGameContent/BoardGameStuff/Cards/ChanceCards/PC_CatchingUp.PC_CatchingUp_C"
local ROOM_LAYOUT = "/Game/CabinGameContent/BoardGameStuff/CardMapLayout_BP.CardMapLayout_BP_C"
local rounds,bases,waiting = {},{},{}
local ownSet = false
local function record(board)
    if not runtime.valid(board) or not board:IsA(BOARD) then return end
    return rounds[board:GetAddress()]
end
local function factor(owner)
    local board = owner:IsA(BOARD) and owner or (owner:IsA(CARD) or owner:IsA(ROOM_LAYOUT)) and owner.GameBoard
    local round = record(board)
    if not round then return 1 end
    if (owner:IsA(CARD) or owner:IsA(ROOM_LAYOUT)) and (board.IntroRewind_TL:IsPlaying() or board.DealCards_TL:IsPlaying()) then return 1 end
    return round.speed
end
mod:bind(SPEED_EVENT,function(context,value)
    local board = context:get()
    local selected = value:get()
    speed.rate(1,selected)
    local existing=record(board)
    rounds[board:GetAddress()]={board=board,speed=selected}
    waiting[board:GetAddress()]=nil
    if not existing or existing.speed~=selected then mod:log("info","round host speed received: " .. selected) end
end)
local function freeze(board)
    if not runtime.valid(board) or not board:HasAuthority() or record(board) then return end
    -- Hook discovery order is unspecified. Wait for the receiver before sending
    -- the first value, so the local acknowledgement cannot race registration.
    if not mod.hooks[SPEED_EVENT].bound then return end
    local selected = mod.store.values.enabled and mod.store.values.speed or 1
    assert(runtime.valid(StaticFindObject(SPEED_EVENT)),"FastTurns board overlay missing")
    board:CabinFastTurnsSpeed_MC(selected)
    assert(record(board) and record(board).speed==selected,"local multicast speed acknowledgement absent")
    mod:log("info","round host speed frozen; remote acknowledgement pending")
end
mod:bind(BOARD .. ":SetCurrentPlayerTurn",function(context) freeze(context:get()) end)
local function selected(timeline)
    if not runtime.valid(timeline) then return end
    local owner = timeline:GetOwner()
    if not runtime.valid(owner) then return end
    local name = timeline:GetFName():ToString()
    local allowed = owner:IsA(BOARD) and speed.board[name] or owner:IsA(CARD) and speed.cards[name]
    if not allowed then return end
    return factor(owner)
end
mod:bind("/Script/Engine.TimelineComponent:SetPlayRate",function(context,rate)
    if ownSet then return end
    local timeline = context:get()
    local multiplier = selected(timeline)
    if not multiplier then return end
    local original = rate:get()
    bases[timeline:GetAddress()]={timeline=timeline,rate=original}
    rate:set(speed.rate(original,multiplier))
end,"pre")
local function start(context)
    local timeline = context:get()
    local multiplier = selected(timeline)
    if not multiplier then return end
    local entry = bases[timeline:GetAddress()]
    if not entry then entry={timeline=timeline,rate=timeline:GetPlayRate()};bases[timeline:GetAddress()]=entry end
    local wanted = speed.rate(entry.rate,multiplier)
    if timeline:GetPlayRate()~=wanted then
        ownSet = true
        local ok,cause = pcall(timeline.SetPlayRate,timeline,wanted)
        ownSet = false
        assert(ok,"timeline play rate apply failed: " .. tostring(cause))
        assert(math.abs(timeline:GetPlayRate()-wanted)<0.0001*math.max(1,math.abs(wanted)),"timeline play rate readback differs")
    end
end
for _,name in ipairs({"Play","PlayFromStart","Reverse","ReverseFromEnd"}) do
    mod:bind("/Script/Engine.TimelineComponent:" .. name,start,"pre")
end
mod:bind("/Script/Engine.KismetSystemLibrary:Delay",function(context,world,duration,latent)
    local owner = world:get()
    if not runtime.valid(owner) then return end
    local info = latent:get()
    local name = info.ExecutionFunction:ToString()
    local allowed = owner:IsA(BOARD) and name=="ExecuteUbergraph_GameBoard_BP" and speed.boardDelays[info.UUID]
        or owner:IsA(CARD) and name=="ExecuteUbergraph_ParentCard" and speed.cardDelays[info.UUID]
        or owner:IsA(CARD) and owner:IsA(THIEF) and name=="ExecuteUbergraph_PC_Thief" and speed.thiefDelays[info.UUID]
        or owner:IsA(CARD) and owner:IsA(CATCHING_UP) and name=="ExecuteUbergraph_PC_CatchingUp" and speed.catchingUpDelays[info.UUID]
        or owner:IsA(ROOM_LAYOUT) and name=="ExecuteUbergraph_CardMapLayout_BP" and speed.roomLayoutDelays[info.UUID]
    if allowed then duration:set(speed.delay(duration:get(),factor(owner))) end
end,"pre")
mod:observe("timeline references",function()
    for address,entry in pairs(bases) do if not runtime.valid(entry.timeline) then bases[address]=nil end end
    for address,entry in pairs(rounds) do if not runtime.valid(entry.board) then rounds[address]=nil end end
    for address,board in pairs(waiting) do if not runtime.valid(board) then waiting[address]=nil end end
end)
local lastBroadcast=0
mod:observe("late client speed",function()
    local now=os.time()
    if now==lastBroadcast then return end
    lastBroadcast=now
    -- A board can start before its Blueprint hook is bound. Recover from the
    -- actual running-round state, never from a client's local speed setting.
    for _,board in ipairs(FindAllOf("GameBoard_BP_C") or {}) do
        if runtime.valid(board) and board.GameStarted==true and runtime.valid(board.CurrentPlayerTurn) then
            freeze(board)
            local address=board:GetAddress()
            if not record(board) and not waiting[address] then
                waiting[address]=board
                mod:log("warn",board:HasAuthority() and "active round awaiting speed receiver hook; native speed retained"
                    or "active round awaiting host speed; native speed retained; check host FastTurns runtime and overlay")
            end
        end
    end
    for _,entry in pairs(rounds) do
        if runtime.valid(entry.board) and entry.board:HasAuthority() then entry.board:CabinFastTurnsSpeed_MC(entry.speed) end
    end
end)
return mod
