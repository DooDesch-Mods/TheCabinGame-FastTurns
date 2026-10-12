local M = {}
M.board = {Rotate_TL=true,AdvancePlayer_TL=true,Visitor_TL=true,FinishVisitor_TL=true,
    PlayerDeath_TL=true,TableTimeShift_TL=true,GiveTime_TL=true}
M.cards = {Eject_Timeline=true,Eject_TL=true,Eject_SelfPlayer_TL=true,
    ResetCardPOS_TL=true,Timeline_1=true,Graveyard_TL=true,Flip_Timeline=true}
M.boardDelays = {
    [-2719087]=true,[-1281726690]=true,[762452849]=true,[1837716280]=true,
    [1373960340]=true,[-613304550]=true,[1484780868]=true,[999013541]=true,
    [1677042955]=true,[377431672]=true,[-1882820629]=true,[420262197]=true,
    [517937255]=true,[-1737487980]=true,[1647222594]=true,[-1043742080]=true,
    [-524346357]=true,[1576945929]=true,[-2013474043]=true,
}
M.cardDelays = {[113569087]=true,[-661100838]=true,[-473459973]=true,
    [-857181867]=true,[-1441898126]=true,[-325550363]=true,[609643387]=true,[398120949]=true}
M.thiefDelays = {[825083586]=true,[-1034458098]=true}
M.catchingUpDelays = {[-1663121935]=true}
M.roomLayoutDelays = {[1008126462]=true}
function M.rate(original,factor)
    assert(type(original)=="number" and original==original and math.abs(original)<math.huge,"original transition rate invalid")
    assert(type(factor)=="number" and factor>0 and factor<math.huge,"speed factor must be finite and positive")
    local result = original*factor
    assert(result==result and math.abs(result)<math.huge,"scaled transition rate overflow")
    return result
end
function M.delay(original,factor) return M.rate(original,1/factor) end
return M
