import random, heapq, math
from math import hypot, inf
random.seed(42)
N, HOP, K = 500, 30.0, 200.0
SOS = (180.0, 30.0)
phones = []
for i in range(N):
    if i % 10 == 0:
        x = SOS[0] + random.gauss(0, 12); y = SOS[1] + random.gauss(0, 12)
    else:
        x = random.uniform(0, K); y = random.uniform(0, K)
    phones.append((x, y))
G = [[] for _ in phones]; edges = 0
for i in range(N):
    for j in range(i + 1, N):
        if hypot(phones[i][0]-phones[j][0], phones[i][1]-phones[j][1]) < HOP:
            G[i].append(j); G[j].append(i); edges += 1

def dijkstra(src):
    dist = [inf]*N; dist[src] = 0; pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]: continue
        for v in G[u]:
            if d + 1 < dist[v]:
                dist[v] = d + 1; heapq.heappush(pq, (d + 1, v))
    return dist

SOSI = min(range(N), key=lambda i: hypot(phones[i][0]-SOS[0], phones[i][1]-SOS[1]))
dist = dijkstra(SOSI)
reach = [i for i in range(N) if dist[i] < inf]
print("RADIO mesh, seeded simulation [SIM:MATH] (deterministic seed 42, no claim of real bytes):")
print("  phones: %d   radio edges (hop<%.0fm): %d   avg degree: %.1f" % (N, HOP, edges, 2.0*edges/N))
print("  SOS radio at phone %d (%d,%d m)" % (SOSI, *phones[SOSI]))
print("  gradient reaches %d/%d of the crowd (%.0f%%)" % (len(reach), N, 100.0*len(reach)/N))
print("  avg hops crowd→SOS: %.2f   max hops: %d" % (sum(dist[i] for i in reach)/len(reach), max(dist[i] for i in reach)))
hop1 = [i for i in range(N) if dist[i] == 1]
if hop1:
    dx = sum(phones[i][0]-phones[SOSI][0] for i in hop1)/len(hop1)
    dy = sum(phones[i][1]-phones[SOSI][1] for i in hop1)/len(hop1)
    print("  hop-1 phones surround SOS at bearing %.0f deg (gradient is spatially TRUE: crowd points home)" % (math.degrees(math.atan2(dy, dx))))
print("  [SIM:MATH] — numeric geometry only. [EXP:NOT-RUN] — no real radios traded bytes. This sim is the paper's gradient RULE, not a radio claim.")
