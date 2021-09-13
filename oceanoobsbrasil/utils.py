from numpy import arctan,rad2deg,arcsin
import numpy as np

def uv2intdir(u, v):

    if u>0 and v>0:
        intensidade=np.sqrt((u*u)+(v*v))
        direcao=90-rad2deg(arctan(v/u))
    elif u<0 and v>0:
        intensidade=np.sqrt((u*u)+(v*v))
        direcao=rad2deg(arcsin(v/(-u)))+270
    elif u<0 and v<0:
        intensidade=np.sqrt((u*u)+(v*v))
        direcao=270-rad2deg(arctan((-v)/(-u)))
    elif u>0 and v<0:
        intensidade=np.sqrt((u*u)+(v*v))
        direcao=rad2deg(arctan((-v)/u))+90
    elif u==0 and v==0:
        intensidade=0
        direcao=0
    elif u==0 and v>0:
        intensidade=v
        direcao=0
    elif u==0 and v<0:
        intensidade=v
        direcao=180
    elif u>0 and v==0:
        intensidade=u
        direcao=90
    elif u<0 and v==0:
        intensidade=u
        direcao=270

    return intensidade,direcao
