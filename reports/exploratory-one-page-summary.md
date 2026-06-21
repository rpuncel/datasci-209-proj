# Exploratory Visualization Summary

Ellie Parker, Mengyao Chen, Tom Dobbs, Rob Puncel  
W209 - Section 4

## Hypothesis 1: AI data center capacity and capital spending are concentrated among a small number of companies and projects.

**What's informative about this view:**  
The owner and site concentration views show that estimated AI data center power is not evenly distributed. The top four owner groups account for about 68.5% of estimated current power, and the top 10 sites account for about 55.3% of estimated current power. The capital-cost scatterplot reinforces the same pattern: the owners with the largest power footprint also carry the largest estimated capital footprint.

**What could be improved about this view:**  
The concentration views show who dominates the dataset, but they do not fully explain why. A later refinement could separate company-owned sites from leased or user-operated sites, and could distinguish observed capital spending from modeled capital-cost estimates.

## Hypothesis 2: AI data center power and capital buildout accelerated after major generative AI milestones.

**What's informative about this view:**  
The timeline view places estimated year-end data center power alongside major AI milestones, including the Attention paper, ChatGPT, GPT-4, and OpenClaw. The chart shows a sharp rise after 2023: estimated portfolio power increases from 435 MW in 2023 to about 17,280 MW in 2026. The annual-additions chart adds nuance by showing that the acceleration is lumpy, with large jumps concentrated in a few years.

**What could be improved about this view:**  
The timeline combines observed, estimated, and planned records. The next improvement would be to visually encode record certainty or project status so completed capacity and planned capacity are easier to distinguish.

## Hypothesis 3: Data center resource intensity varies substantially by project and geography, suggesting some sites and regions may be more environmentally or operationally stressed than others.

**What's informative about this view:**  
The compute-density scatterplot shows that current power does not translate into compute capacity evenly. Sites with similar power can have very different H100-equivalent density, and some high-power sites sit below the median density level. The geography views add another layer: estimated power is heavily concentrated in North America and unevenly distributed across U.S. states.

**What could be improved about this view:**  
Compute density is a useful proxy, but it does not directly measure environmental stress. To strengthen this hypothesis, the dashboard should eventually join data center locations to regional electricity prices, grid capacity, water availability, drought conditions, or permitting data.

## Conclusion

The exploratory dashboard supports three main findings. AI data center infrastructure is concentrated among a small number of companies and sites. The buildout pipeline accelerates sharply after the generative AI boom. Resource intensity varies by project and geography, making location and compute density important context for understanding infrastructure pressure.
