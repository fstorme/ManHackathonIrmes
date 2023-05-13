# Manchester City Hackathon
## Team 
Matéo, Tom, Nathan, Clément et Florent

## Summary

This repisitory gather the code behind our submission to the Manchester City hackathon for their female football team.
Our approach aims to help coachs take decision during matches by giving metrics summarizing the physiscal state of players as well as well as their tactical awarness in real time. 

Firstly, we computed the metabolic cost and metabolic power of shuttle sprints based on accelration and speed of players. These features are then used in a hidden markov model to obtain a real-time latent state for the intensity of the effort of a given player. The time spent in the highest intensity state is then used as a proxy for physical freshness. Even though time spent in highest metabolic intensities are small with respect to a full game, [they are believed to be very influencial in the outcome of a match.](https://link.springer.com/article/10.1007/s40279-022-01791-z)

Secondly, we trained an expected pass model as a basis for a tactical awarness indicator for the different players. This indicator coupled to a game-phase analysis leads to the identification of favored ball path through the team and hopefully leading to a goal.

## Content

The [script](https://github.com/fstorme/ManHackathonIrsem/tree/main/scripts) contains the main script for data loading and processing. The [examples](https://github.com/fstorme/ManHackathonIrsem/tree/main/examples) contains notebooks that are at the core of our submission in particular [HMM on metabolic data.ipynb](https://github.com/fstorme/ManHackathonIrsem/blob/main/examples/HMM%20on%20metabolic%20data.ipynb) and [Example match for metabolic analysis](https://github.com/fstorme/ManHackathonIrsem/blob/main/examples/Example%20Match%20for%20Metabolic%20analysis.ipynb) that are respiectvely used to train, select and apply the HMM model.

The work concerning the expected pass models is contained in the xPass Branch pending merging. 

The [asset](https://github.com/fstorme/ManHackathonIrsem/tree/main/assets) contains the files used in the figma demo associated to our submission. The [models](https://github.com/fstorme/ManHackathonIrsem/tree/main/models) contain the selected metabolic model.

## Requirement 

The requirement are given in [requirements.txt](https://github.com/fstorme/ManHackathonIrsem/blob/main/requirements.txt)
