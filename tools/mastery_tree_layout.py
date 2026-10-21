"""Occupied milestone columns and rooted paths for the private mastery UI."""
import textwrap

LEVELS=(5,10,15,20,25,30)
NODE_SIZE=96
NODE_WIDTH=50
NODE_HEIGHT=28
ROOT=(98,102,58,28)
ORIGIN=(156,116)
FIRST_COLUMN=174
COLUMN_STEP=55


def connections(row):
    """Every independent path starts at the same visible root, then runs right."""
    nodes=row['nodes']
    links=[]
    for index,n in enumerate(nodes):
        cy=n['y']+NODE_HEIGHT//2
        if n['parent']>=0:
            start=nodes[n['parent']]['x']+NODE_WIDTH
        else:
            # Short diagonal fans are native rectangles; all meet exactly at
            # the root midpoint. Long branches continue horizontally afterward.
            x0,y0=row['origin']
            dx,dy=18,cy-y0
            steps=max(abs(dx),abs(dy),1)
            points=[(round(x0+dx*i/steps),round(y0+dy*i/steps)) for i in range(steps+1)]
            links.extend((x,y,1,1,index) for x,y in dict.fromkeys(points))
            start=x0+18
        if n['x']>start:links.append((start,cy,n['x']-start,1,index))
    return links

def prepare(rows):
    for row in rows:
        nodes=row['nodes']
        lanes=max(n['lane'] for n in nodes)+1
        assert lanes<=4
        # Only occupied milestone columns need space. Wider cards keep complete
        # faculty names legible without squeezing six mostly empty columns.
        levels=sorted({n['required'] for n in nodes},key=lambda v:v or 100000)
        assert len(levels)<=5
        for i,n in enumerate(nodes):
            col=levels.index(n['required'])
            n['x']=FIRST_COLUMN+COLUMN_STEP*col
            n['y']=ORIGIN[1]-NODE_HEIGHT//2-(lanes-1)*14+28*n['lane']
            n['title_lines']=[textwrap.wrap(t,16,break_long_words=False,break_on_hyphens=False)
                              for t in n['title']]
            assert all(1<=len(lines)<=2 for lines in n['title_lines']),n['title']
            # Source order is semantic, not necessarily level order.
            earlier=[j for j,p in enumerate(nodes) if p['lane']==n['lane'] and
                     (p['required'] or 99)<(n['required'] or 99)]
            n['parent']=max(earlier,key=lambda j:nodes[j]['required']) if earlier else -1
        assert len({(n['x'],n['y']) for n in nodes})==len(nodes)
        # The sidebar and root remain fixed; center the occupied milestone
        # columns inside the available tree area, without crowding the list.
        right=max(n['x']+NODE_WIDTH for n in nodes)
        shift=(444-right)//2
        row['root']=ROOT
        row['origin']=ORIGIN
        for n in nodes:n['x']+=shift
        for i,n in enumerate(nodes):
            neighbors=[]
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                candidates=[j for j,p in enumerate(nodes) if
                    ((p['y']==n['y'] and (p['x']-n['x'])*dx>0) if dx else (p['y']-n['y'])*dy>0)]
                neighbors.append(min(candidates,key=lambda j:
                    abs(nodes[j]['y']-n['y'])*1000+abs(nodes[j]['x']-n['x'])) if candidates else i)
            n['neighbors']=neighbors
            n['lines']=[textwrap.wrap(' '.join(filter(None,(n['description'][lang],n['detail'][lang]))),72)
                        for lang in range(2)]
            assert all(len(lines)<=4 for lines in n['lines']),n
    return rows
