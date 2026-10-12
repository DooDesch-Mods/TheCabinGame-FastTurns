"""Exercise the shipped delay hook through the owning runtime registration."""
from pathlib import Path
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "Mods/CabinFastTurns/Scripts"
vm = LuaRuntime(unpack_returned_tuples=True)
vm.globals().directory = SCRIPTS.as_posix()
vm.execute('package.path=directory.."/?.lua;"..package.path')
vm.execute(r'''
local store={values={enabled=true,speed=2}}
package.preload.cabin_store=function() return {new=function() return store end} end
package.preload.cabin_registry=function()
    return {new=function() return {register=function() end,poll=function() end} end}
end
package.preload.cabin_host_settings=function() return {start=function() end} end
local registered={}
local tick
IsInGameThread=function() return true end
LoopInGameThreadWithDelay=function(_,callback) tick=callback;return 1 end
IsValidDelayedActionHandle=function(handle) return handle==1 end
StaticFindObject=function() return {IsValid=function() return true end} end
RegisterHook=function(path,pre,post)
    registered[path]={pre=pre,post=post}
    return 1,2
end
local BOARD='/Game/CabinGameContent/BoardGameStuff/Board/GameBoard_BP.GameBoard_BP_C'
local CARD='/Game/CabinGameContent/BoardGameStuff/Cards/ParentCard.ParentCard_C'
local THIEF='/Game/CabinGameContent/BoardGameStuff/Cards/ChanceCards/PC_Thief.PC_Thief_C'
local CATCHING_UP='/Game/CabinGameContent/BoardGameStuff/Cards/ChanceCards/PC_CatchingUp.PC_CatchingUp_C'
local ROOM_LAYOUT='/Game/CabinGameContent/BoardGameStuff/CardMapLayout_BP.CardMapLayout_BP_C'
local DELAY='/Script/Engine.KismetSystemLibrary:Delay'
local function parameter(value)
    return {get=function() return value end,set=function(_,nextValue) value=nextValue end}
end
local function owner(class,address,parents)
    return {IsValid=function(self) return not self.invalid end,
        IsA=function(_,wanted) return class==wanted or parents and parents[wanted]==true or false end,
        GetAddress=function() return address end,HasAuthority=function() return true end}
end
local board=owner(BOARD,100)
board.IntroRewind_TL={IsPlaying=function() return board.intro==true end}
board.DealCards_TL={IsPlaying=function() return board.deal==true end}
board.CabinFastTurnsSpeed_MC=function(self,value)
    registered[BOARD..':CabinFastTurnsSpeed_MC'].pre(parameter(self),parameter(value))
end
local mod=assert(loadfile(directory..'/main.lua'))()
tick()
assert(mod.hooks[DELAY].bound and mod.hooks[DELAY].phase=='pre')
assert(registered[DELAY].post==nil)
local delay=registered[DELAY].pre
local function observed(target,uuid,seconds,name)
    local duration=parameter(seconds)
    local info={UUID=uuid,ExecutionFunction={ToString=function() return name or 'ExecuteUbergraph_GameBoard_BP' end}}
    delay(parameter(nil),parameter(target),duration,parameter(info))
    return duration:get()
end
assert(observed(board,-524346357,2)==2,'unstarted round must keep native duration')
registered[BOARD..':SetCurrentPlayerTurn'].pre(parameter(board))
assert(observed(board,-2719087,1)==0.5,'end-turn wait must use round speed')
assert(observed(board,-524346357,2)==1,'rotation wait must use round speed')
assert(observed(board,-1043742080,3)==1.5,'fourth-turn wait must use round speed')
assert(math.abs(observed(board,1373960340,1.5299999713897705)-0.7649999856948853)<1e-12)
store.values.speed=5
assert(observed(board,-524346357,2)==1,'settings change must not replace frozen round speed')
registered[BOARD..':CabinFastTurnsSpeed_MC'].pre(parameter(board),parameter(5))
assert(observed(board,-524346357,2)==0.4,'received round speed must change transition duration')
registered[BOARD..':CabinFastTurnsSpeed_MC'].pre(parameter(board),parameter(1))
assert(observed(board,-524346357,2)==2,'speed one must preserve native duration')
registered[BOARD..':CabinFastTurnsSpeed_MC'].pre(parameter(board),parameter(2))
assert(observed(board,-524346357,2,'ExecuteUbergraph_ParentCard')==2,'wrong execution function must be excluded')
for _,uuid in ipairs({-1888610176,562893017,-1302583400,-1612436099,-417187111,
    -1437267012,971731272,842758640,-1779349800,-1433262331,1760059324,1373373398}) do
    assert(observed(board,uuid,5)==5,'unlisted wait must remain native: '..uuid)
end
local foreign=owner('/Game/Other.Other_C',101)
assert(observed(foreign,-524346357,2)==2,'foreign actor must be excluded')
local stale=owner(BOARD,102);stale.invalid=true
assert(observed(stale,-524346357,2)==2,'invalid actor must be excluded')
local card=owner(CARD,103);card.GameBoard=board
assert(observed(card,113569087,2,'ExecuteUbergraph_ParentCard')==1)
board.intro=true
assert(observed(card,113569087,2,'ExecuteUbergraph_ParentCard')==2,'intro card delay must remain native')
board.intro=false;board.deal=true
assert(observed(card,113569087,2,'ExecuteUbergraph_ParentCard')==2,'dealing card delay must remain native')
board.deal=false
assert(observed(card,113569087,2,'ExecuteUbergraph_GameBoard_BP')==2)
local thief=owner(THIEF,104,{[CARD]=true});thief.GameBoard=board
assert(observed(thief,825083586,5,'ExecuteUbergraph_PC_Thief')==2.5)
assert(observed(thief,-1034458098,2,'ExecuteUbergraph_PC_Thief')==1)
registered[BOARD..':CabinFastTurnsSpeed_MC'].pre(parameter(board),parameter(5))
assert(observed(thief,825083586,5,'ExecuteUbergraph_PC_Thief')==1)
assert(observed(thief,-1034458098,2,'ExecuteUbergraph_PC_Thief')==0.4)
assert(observed(thief,1290396607,2,'ExecuteUbergraph_PC_Thief')==2,'pre-event Thief delay must remain native')
assert(observed(thief,825083586,5,'ExecuteUbergraph_ParentCard')==5,'wrong execution function must be excluded')
assert(observed(card,825083586,5,'ExecuteUbergraph_PC_Thief')==5,'other ParentCard must be excluded')
assert(observed(board,825083586,5,'ExecuteUbergraph_PC_Thief')==5,'board UUID collision must be excluded')
local derivative=owner('/Game/Test/DerivedThief.DerivedThief_C',105,{[CARD]=true,[THIEF]=true})
derivative.GameBoard=board
assert(observed(derivative,825083586,5,'ExecuteUbergraph_PC_Thief')==1,'inherited Thief graph must use frozen speed')
assert(observed(derivative,825083586,5,'ExecuteUbergraph_DerivedThief')==5,'derived own graph must be excluded')
local unrelated=owner('/Game/Other.Other_C',106);unrelated.GameBoard=board
assert(observed(unrelated,825083586,5,'ExecuteUbergraph_PC_Thief')==5)
local unstarted=owner(BOARD,107)
thief.GameBoard=unstarted
assert(observed(thief,825083586,5,'ExecuteUbergraph_PC_Thief')==5,'unstarted round must preserve caller wait')
thief.GameBoard=board
board.intro=true
assert(observed(thief,825083586,5,'ExecuteUbergraph_PC_Thief')==5,'intro caller wait must remain native')
board.intro=false;board.deal=true
assert(observed(thief,-1034458098,2,'ExecuteUbergraph_PC_Thief')==2,'dealing caller wait must remain native')
board.deal=false
registered[BOARD..':CabinFastTurnsSpeed_MC'].pre(parameter(board),parameter(1))
assert(observed(thief,825083586,5,'ExecuteUbergraph_PC_Thief')==5,'speed one must preserve caller wait')
assert(observed(thief,-1034458098,2,'ExecuteUbergraph_PC_Thief')==2)
local catchingUp=owner(CATCHING_UP,108,{[CARD]=true});catchingUp.GameBoard=board
assert(observed(catchingUp,-1663121935,7,'ExecuteUbergraph_PC_CatchingUp')==7)
registered[BOARD..':CabinFastTurnsSpeed_MC'].pre(parameter(board),parameter(5))
assert(math.abs(observed(catchingUp,-1663121935,7,'ExecuteUbergraph_PC_CatchingUp')-1.4)<1e-12)
assert(observed(catchingUp,-258623404,1,'ExecuteUbergraph_PC_CatchingUp')==1,'pre-movement wait must remain native')
assert(observed(catchingUp,2103269924,1,'ExecuteUbergraph_PC_CatchingUp')==1,'parallel card-location update must remain native')
assert(observed(catchingUp,-1663121935,7,'ExecuteUbergraph_ParentCard')==7)
assert(observed(thief,-1663121935,7,'ExecuteUbergraph_PC_CatchingUp')==7,'other chance-card class must be excluded')
assert(observed(catchingUp,825083586,5,'ExecuteUbergraph_PC_Thief')==5)
assert(observed(card,-1663121935,7,'ExecuteUbergraph_PC_CatchingUp')==7)
assert(observed(unrelated,-1663121935,7,'ExecuteUbergraph_PC_CatchingUp')==7)
local inherited=owner('/Game/Test/DerivedCatchingUp.DerivedCatchingUp_C',109,{[CARD]=true,[CATCHING_UP]=true})
inherited.GameBoard=board
assert(math.abs(observed(inherited,-1663121935,7,'ExecuteUbergraph_PC_CatchingUp')-1.4)<1e-12)
assert(observed(inherited,-1663121935,7,'ExecuteUbergraph_DerivedCatchingUp')==7)
board.intro=true
assert(observed(catchingUp,-1663121935,7,'ExecuteUbergraph_PC_CatchingUp')==7)
board.intro=false;board.deal=true
assert(observed(catchingUp,-1663121935,7,'ExecuteUbergraph_PC_CatchingUp')==7)
board.deal=false
catchingUp.GameBoard=unstarted
assert(observed(catchingUp,-1663121935,7,'ExecuteUbergraph_PC_CatchingUp')==7)
catchingUp.GameBoard=board;catchingUp.invalid=true
assert(observed(catchingUp,-1663121935,7,'ExecuteUbergraph_PC_CatchingUp')==7)
local layout=owner(ROOM_LAYOUT,110);layout.GameBoard=board
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==1)
registered[BOARD..':CabinFastTurnsSpeed_MC'].pre(parameter(board),parameter(2))
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==2.5)
store.values.speed=5
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==2.5,'layout wait must use frozen round speed')
assert(observed(layout,-1156500248,5,'ExecuteUbergraph_CardMapLayout_BP')==5,'initial card deal wait must remain native')
assert(observed(layout,-111059295,0.1,'ExecuteUbergraph_CardMapLayout_BP')==0.1,'detector update wait must remain native')
assert(observed(layout,1008126462,5,'ExecuteUbergraph_ParentCard')==5)
assert(observed(card,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5)
assert(observed(board,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5)
assert(observed(unrelated,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5)
local derivedLayout=owner('/Game/Test/DerivedLayout.DerivedLayout_C',111,{[ROOM_LAYOUT]=true})
derivedLayout.GameBoard=board
assert(observed(derivedLayout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==2.5)
assert(observed(derivedLayout,1008126462,5,'ExecuteUbergraph_DerivedLayout')==5)
board.intro=true
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5)
board.intro=false;board.deal=true
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5)
board.deal=false
layout.GameBoard=unstarted
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5)
layout.GameBoard=unrelated
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5,'foreign GameBoard must be excluded')
layout.GameBoard=nil
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5)
layout.GameBoard=board
board.invalid=true
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5,'stale bound GameBoard must preserve native wait')
board.invalid=false
registered[BOARD..':CabinFastTurnsSpeed_MC'].pre(parameter(board),parameter(1))
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5)
layout.invalid=true
assert(observed(layout,1008126462,5,'ExecuteUbergraph_CardMapLayout_BP')==5)
local speed=require('speed')
assert(not speed.board.IntroRewind_TL and not speed.board.DealCards_TL and not speed.cards.CursorHover_TL)
''')
print("info: FastTurns: owning runtime delay hook, frozen speed and exclusions passed; native dispatch pending")
