library(here)
library("sandwich")
library(ggplot2)

## load in data
df = read.csv(here("data", "did-data.csv"))

## TWFE regression
df$treated = (df$post) * (df$treat)
lr_main = lm(data = df, ttc_d ~ 0 + as.factor(id) + time + treated)
print("TWFE results:")
print(coef(summary(lr_main))["treated",])


## Event Study Plot
plot_es <- function(lr, title) {
  nm <- grep("treat:.*", names(lr$coeff))
  coef <- lr$coeff[nm]
  se <- sqrt(diag(vcovHC(lr, type = "HC1")))
  cv <- qnorm(1 - .05 / 2) # 95% confidence interval
  cilb <- coef - cv * se[nm]
  ciub <- coef + cv * se[nm]
  plotdf <- data.frame(year = c(1:4, 6:9), coef = coef, cilb =
                         cilb, ciub = ciub)
  p <- ggplot(data = plotdf, aes(x = year, y = coef)) +
    geom_point() +
    geom_errorbar(aes(ymin = cilb, ymax = ciub)) +
    geom_hline(aes(yintercept = 0), linetype = "dotted") +
    geom_vline(aes(xintercept = 5), linetype = "dotted") +
    geom_label(label = "base \n period", x = 5, y = 0) +
    ylim(1.1 * min(cilb), 1.1 * max(ciub)) + 
    # annotate(geom = "text", label = "base period", x = 2005, y = -.017,
    # angle = 90) +
    scale_x_continuous(breaks = plotdf$year) +
    labs(x = "Quarter", y = "Coefficient on interaction") +
    ggtitle(title)
  return(p)
}


## Event Study
df$time = relevel(as.factor(df$time), 4)
lr = lm(data = df, ttc_d ~ treat * time)
plot_es(lr, "Event Study")
