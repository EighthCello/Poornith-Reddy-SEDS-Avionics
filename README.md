# Poornith-Reddy-SEDS-Avionics
SEDS Avionics induction.

Note: I've marked the areas in which AI was used in the comments

The biggest problem was obviously the errors. In my code, I've called them anomalies. (Spider-man ATSV reference)
For now, anomalies are detected if a) they're non-numeric or b) if they're extreme values.
Now, checking for non-numeric values is easy, but how would I detect which value is "extreme"?

I used the Hampell technique. In essence, I take the median of neighbouring data points from a local argument (example, 5 neighbours on each side) and then check the standard deviation. Something like, take every point in the window, find how far it is from the median, then take the median of those distances.
If it's higher than a certain value, its flagged as an anomaly.(Plotted in Red color points.) After detecting, it takes the mean value and corrects the anomaly.

I also added a noise reducing argument (--noisered) which takes the mean AFTER detecting and correcting the anomalies, and smoothens the curve using the moving average.
