"""Three isolated Lua states exercise initialization and host-owned speed recovery.

The transport seam deliberately drops messages. Actual Unreal RPC delivery still
requires a multiplayer game run.
"""
from pathlib import Path
from lupa.lua54 import LuaRuntime

SCRIPTS = Path(globals().get('scripts_under_test', Path(__file__).resolve().parents[1] / 'Mods/CabinFastTurns/Scripts'))
peers = []
delivered = []


def multicast(value):
    delivered.append(value)
    for peer in peers:
        if peer.globals().connected:
            peer.globals().receive(value)


def client(authority, speed):
    vm = LuaRuntime(unpack_returned_tuples=True)
    vm.globals().directory = SCRIPTS.as_posix()
    vm.globals().authority = authority
    vm.globals().configured_speed = speed
    vm.globals().broadcast = multicast
    vm.execute(r'''
package.path=directory..'/?.lua;'..package.path
store={values={enabled=true,speed=configured_speed}}
package.preload.cabin_store=function() return {new=function() return store end} end
package.preload.cabin_registry=function() return {new=function() return {register=function() end,poll=function() end} end} end
package.preload.cabin_host_settings=function() return {start=function() end} end
registered={};logs={};seconds=10;connected=true;receiverReady=false
os.time=function() return seconds end
print=function(message) logs[#logs+1]=message end
IsInGameThread=function() return true end
LoopInGameThreadWithDelay=function(_,callback) tick=callback;return 1 end
IsValidDelayedActionHandle=function() return true end
BOARD='/Game/CabinGameContent/BoardGameStuff/Board/GameBoard_BP.GameBoard_BP_C'
EVENT=BOARD..':CabinFastTurnsSpeed_MC'
StaticFindObject=function(path) return {IsValid=function() return path~=EVENT or receiverReady end} end
RegisterHook=function(path,pre,post) registered[path]={pre=pre,post=post};return 1,2 end
function parameter(value) return {get=function() return value end,set=function(_,nextValue) value=nextValue end} end
function newboard(address)
    local b={GameStarted=true,CurrentPlayerTurn={IsValid=function() return true end}}
    function b:IsValid() return not self.invalid end
    function b:IsA(class) return class==BOARD end
    function b:GetAddress() return address end
    function b:HasAuthority() return authority end
    function b:CabinFastTurnsSpeed_MC(value) assert(authority,'client tried to publish speed');broadcast(value) end
    return b
end
board=newboard(1)
FindAllOf=function(name) assert(name=='GameBoard_BP_C');return {board} end
function receive(value)
    local hook=registered[EVENT]
    if hook then hook.pre(parameter(board),parameter(value)) end
end
function duration()
    local result=parameter(2)
    registered['/Script/Engine.KismetSystemLibrary:Delay'].pre(parameter(nil),parameter(board),result,
        parameter({UUID=-524346357,ExecutionFunction={ToString=function() return 'ExecuteUbergraph_GameBoard_BP' end}}))
    return result:get()
end
mod=assert(loadfile(directory..'/main.lua'))()
''')
    peers.append(vm)
    return vm


host, first, late = client(True, 2), client(False, 5), client(False, 4)
for peer in peers:
    peer.execute('tick()')
assert not delivered, 'unbound receiver must not publish a speed'
host.execute("registered[BOARD..':SetCurrentPlayerTurn'].pre(parameter(board))")
assert not delivered, 'turn callback before receiver binding must remain recoverable'
for peer in peers:
    peer.execute('receiverReady=true')
for peer in [first, late]:
    peer.execute('seconds=11;tick();assert(duration()==2)')
late.execute('connected=false')
host.execute('seconds=11;tick()')
assert delivered and delivered[0] == 2
for peer in [host, first]:
    peer.execute('assert(duration()==1)')
late.execute('assert(duration()==2);connected=true')
host.execute('store.values.speed=5;seconds=12;tick()')
for peer in peers:
    peer.execute('assert(duration()==1)')
assert delivered[-1] == 2, 'late client must receive frozen host speed, not current local preferences'
before = len(delivered)
for peer in peers:
    peer.execute('tick();tick()')
assert len(delivered) == before, 'rebroadcast must be bounded to one poll per second'
for peer in peers:
    peer.execute('board.invalid=true;board=newboard(2);board.GameStarted=false;seconds=13;tick()')
assert len(delivered) == before, 'new lobby must not freeze a speed before a round starts'
for peer in peers:
    peer.execute('board.GameStarted=true')
host.execute('store.values.enabled=false;seconds=14;tick()')
for peer in peers:
    peer.execute('assert(duration()==2)')
assert delivered[-1] == 1, 'disabled host must control all clients despite their local speed settings'
print('info: 3 Lua states: missed round hook, receiver race, lost first message, late join, frozen settings and disabled host passed; Unreal transport pending')
