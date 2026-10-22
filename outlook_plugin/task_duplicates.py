"""Read-only duplicate hints; never delete or merge the user's saved work."""
from .task_workflow import same_action


def annotate(data):
    groups={key:[dict(t) for t in values] for key,values in data.items()}
    rows=[t for values in groups.values() for t in values if not t.get('completed')]
    parents=list(range(len(rows)))
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for i,a in enumerate(rows):
        for j in range(i):
            b=rows[j]
            if a.get('project_id','')!=b.get('project_id',''):continue
            if same_action(a,b):parents[root(i)]=root(j)
    clusters={}
    for i,row in enumerate(rows):clusters.setdefault(root(i),[]).append(row)
    for members in clusters.values():
        if len(members)<2:continue
        for row in members:row['possible_duplicates']=[other['id'] for other in members if other['id']!=row['id']]
    return groups
