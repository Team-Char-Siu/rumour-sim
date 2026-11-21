# Notes

Project notes. Based on Le Nguyen's mobile-agent disease simulation [1].
Friendship, correction, avoidance and the subject are our additions, not exact
parts of the article.

## States

$$
\text{Unaware} \rightarrow \text{Spreader or Stifler},
\qquad
\text{Spreader} \rightarrow \text{Stifler or Corrector},
\qquad
\text{Corrector} \rightarrow \text{Stifler}.
$$

- Spreaders share the rumour.
- Correctors share the correction.
- Stiflers are inactive.
- Belief, sharing, friendship and avoidance are separate.
- Correction removes belief/avoidance but does not fix friendships.

There are four groups in a 100x100 world. One patient zero starts in group A.
One subject starts in group D. Some friends start near the subject.

## Rumour and correction

For agent $i$:

- $g_i$ = gullibility
- $o_i$ = correction openness
- $\beta_r$ = rumour strength
- $\beta_c$ = correction strength
- $n^r_i$ = nearby active spreaders
- $n^c_i$ = nearby active correctors

$$
P_r(i)=1-(1-g_i\beta_r)^{n^r_i}
$$

$$
P_c(i)=1-(1-o_i\beta_c)^{n^c_i}
$$

This is the usual "at least one success" calculation:

$$
P(\text{at least one})=1-\prod_j(1-p_j).
$$

If both rumour and correction succeed, a coin decides which one is used.
Sender credit is picked from nearby active senders. We sample from the old
states, then apply changes after the step.

If a rumour is accepted, the agent shares it with probability:

$$
P(\text{share})=m+(1-m)s_i,
$$

where $m$ is minimum interest and $s_i$ is sharing tendency. If they accept but
do not share, they become a silent believer.

The basic spreader/stifler idea comes from rumour models such as Maki-Thompson [3].
The article's main idea is that spreaders can pass rumours to unaware agents and
then stop spreading. [1][2]

## Friends and avoidance

When a friend first believes the rumour:

$$
P(\text{friendship ends})=1-\ell_i,
$$

where $\ell_i$ is loyalty. They then avoid the subject.

Non-friends may also start avoiding with some probability. Loyal friends can
stay nearby.

Avoidance has a hard radius and a soft outer zone. If $d$ is the distance from
the subject, $r_h$ is the hard radius and $r_o$ is the outer radius:

$$
\Delta p=\text{step}\cdot\frac{r_o-d}{r_o-r_h}.
$$

## Movement

Agents start inside their group circle using:

$$
\theta=2\pi U_1,
\qquad
r=R\sqrt{U_2}.
$$

The square root is needed so points are spread evenly over the circle area,
not clustered in the middle. [4]

Agents random walk. Group members can visit another group, stay there, then go
home. No-group agents move anywhere.

## Update order

1. Subject notices avoiders.
2. Subject moves.
3. Everyone else moves / avoids.
4. Timers expire.
5. Rumour and correction are sampled from the old states.
6. State changes are applied.
7. Counts are recorded.

## Counts

$$
N_k(t)=\sum_i \mathbf{1}\{s_i(t)=k\}.
$$

Direct people told by agent $j$:

$$
T_j=\sum_i \mathbf{1}\{\text{infector}_i=j\}.
$$

This is direct recipients only, not everyone further down the chain.

## Settings

| Setting | Value |
|---|---:|
| Population | 500 |
| Steps | 400 |
| Seed | 42 |
| Group radius | 15 |
| Correction strength | 0.03 |
| Correction duration | 50 |
| Rumour strength | 0.06 |
| Rumour duration | 50 |

Contact radius:

$$
r_c=4\sqrt{\frac{500}{N}}.
$$

## Problems

- Current RNG is global, so draw order matters.
- Same seed does not guarantee the same result across code versions.
- Contact checking uses dense $N \times N$ matrices, so it is $O(N^2)$.
- Social rules are our assumptions, not proof from the article.

## To do

- [x] Agents, groups, no-group agents, movement, visiting
- [x] Rumour + correction spread, stifling
- [x] Live window + headless mode + plots
- [ ] Seeded RNG per (seed, step, agent)
- [ ] NumPy array version
- [ ] Parallel version (Numba)
- [ ] Serial vs parallel equivalence test
- [ ] Benchmarks (absolute time, speed-up, efficiency)

## References

1. Le Nguyen, *Simulation 102: Agent-Based Disease Modeling*, Medium, 2023.  
   https://medium.com/@ln8378/simulation-102-agent-based-disease-modeling-17307f2de2f3
2. Hayes, *Rumours and Errours*, American Scientist.  
   https://www.americanscientist.org/article/rumours-and-errours
3. *The Maki-Thompson rumour model: a detailed analysis*.  
   https://www.sciencedirect.com/science/article/abs/pii/S1364815200000293
4. Uniform random points in a circle.  
   https://math.stackexchange.com/questions/1307287/random-uniformly-distributed-points-in-a-circle
