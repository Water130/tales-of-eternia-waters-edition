"""Occupied milestone columns and rooted paths for the private mastery UI."""
import textwrap
import math

LEVELS=(5,10,15,20,25,30)
NODE_SIZE=96
NODE_WIDTH=42
NODE_HEIGHT=28
ROOT=(98,118,58,28)
ORIGIN=(156,132)
FIRST_COLUMN=174
COLUMN_STEP=45


def connections(row):
    """Every independent path starts at the same visible root, then runs right."""
    nodes=row['nodes']
    links=[]
    for index,n in enumerate(nodes):
        cy=n['y']+NODE_HEIGHT//2
        if n['parent']>=0:
            start=nodes[n['parent']]['x']+NODE_WIDTH
            points=[(float(start),float(cy))]
        else:
            # Subpixel cubic fan: horizontal tangents at both ends. A continuous
            # ribbon replaces the former staircase of rounded 1x1 rectangles.
            x0,y0=row['origin']
            start=min(x0+28,n['x'])
            steps=24 if cy!=y0 else 1
            points=[(x0+(start-x0)*i/steps,y0+(cy-y0)*(3*(i/steps)**2-2*(i/steps)**3))
                    for i in range(steps+1)]
        if n['x']>start:points.append((float(n['x']),float(cy)))
        links.append(dict(node=index,points=points))
    return links


def ribbon(points, width):
    """Triangle-strip coordinates, with shared joins instead of overlapping tiles."""
    vertices=[]
    for i,(x,y) in enumerate(points):
        a=points[max(0,i-1)];b=points[min(len(points)-1,i+1)]
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=math.hypot(dx,dy)
        assert length>0
        nx,ny=-dy/length*width/2,dx/length*width/2
        vertices.extend(((x+nx,y+ny),(x-nx,y-ny)))
    return vertices

def prepare(rows):
    for row in rows:
        nodes=row['nodes']
        lanes=max(n['lane'] for n in nodes)+1
        assert lanes<=4
        # Only occupied milestone columns need space. Wider cards keep complete
        # faculty names legible without squeezing six mostly empty columns.
        levels=sorted({n['required'] for n in nodes},key=lambda v:v or 100000)
        assert len(levels)<=(5 if row['kind']==2 else 6)
        for i,n in enumerate(nodes):
            col=(levels.index(n['required']) if row['kind']==2 else
                 LEVELS.index(n['required']) if n['required'] in LEVELS else 5)
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
        shift=0
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
            n['lines']=[textwrap.wrap(' '.join(filter(None,(n['description'][lang],n['detail'][lang]))),60 if row['kind']==0 else 94)
                        for lang in range(2)]
            assert all(len(lines)<=(4 if row['kind']==0 else 3) for lines in n['lines']),n
    return rows
