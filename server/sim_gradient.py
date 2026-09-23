import random, heapq
from math import hypot, inf
random.seed(42)
N = 500
K = 200.0
HOP = 3.0
SOS = (180.0, 30.0)
phones = []
for i in range(N):
    if i < 40:
        x = SOS[0] + random.gauss(0, 12)
        y = SOS[1] + random.gauss(0, 12)
    else:
        x = random.uniform(0, K); y = random.uniform(0, K)
    phones.append((x, y))
G = [[] for _ in phones]
edges = 0
for i in range(N):
    for j in range(i + 1, N):
        if hypot(phones[i][0]-phones[j][0], phones[i][1]-phones[j][1]) < HOP:
            G[i].append(j); G[j].append(i); edges += 1

def gradient_src(src):
    dist = [inf]*N; dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]: continue
        for v in G[u]:
            if d + 1 < dist[v]:
                dist[v] = d + 1; heapq.heappush(pq, (d + 1, v))
    return dist

SOSI = 0
for i, p in enumerate(phones):
    if hypot(p[0]-SOS[0], p[1]-SOS[1]) < 5:
        SOSI = i; break
dist = gradient_src(SOSI)
reachable = sum(1 for d in dist if d < inf)
print("RADIO Graph (deterministic seed 42):")
print("  phones               : %d" % N)
print("  radio edges (hop<=%.1fm): %d   avg degree %.1f" % (HOP, edges, 2*edges/N))
print("  hops from SOS -> crowd : avg %.2f  max %d  reaching %d/%d" % (sum(d for d in dist if d<inf)/reachable, max(d for d in dist if d<inf), reachable, N))
print("  gradient closes (<=4 hops reaches the crowd direction) : %d/%d" % (sum(1 for d in dist if d <= 4), N))
print("SOS GRADIENT (the paper rule: follow decreasing hop-distance to SOS):")
printn = 0
for i in range(N):
    if dist[i] < inf and dist[i] > 0:
        nxt = [v for v in G[i] if dist[v] == dist[i]-1]
        if nxt:
            x = sum(phones[v][0] for v in nxt)/len(nxt)
            y = sum(phones[v][1] for v in nxt)/len(nxt)
            dx, dy = x-phones[i][0], y-phones[i][1]
            ang = math.degrees(math.atan2(dy, dx)) if dx or dy else -999
            printn += 1
            if printn <= 8:
                print("  phone %-3d (%.0f,%.0f) -> hop-1 neighbor (%.0f,%.0f)  bearing %.0f deg toward SOS" % (i, phones[i][0], phones[i][1], x, y, ang))
print("  ... every gradient-steerable phone points DOWNHILL toward the SOS radio = the crowd 'finds us'")
