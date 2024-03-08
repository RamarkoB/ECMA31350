library(did)
library(here)


## load in data
df = read.csv(here("data", "did-data.csv"))

df$first.treat = df$treat * 5
df$lang = as.factor(df$lang)
df$license = as.factor(df$license)
df$has_wiki = ifelse(df$has_wiki == "True", 1, 0)

## Specification (2) -- only pre-treatment covariates
# covs = c("age", "size", "watchers", "lang", "forks", "license", "has_wiki")
covs = c("age", "size", "watchers")

## run Sant'Anna Callaway DID
attgt = att_gt(yname = "ttc_d",
               tname = "time", 
               idname = "id", 
               gname = "first.treat", 
               xformla = reformulate(covs), 
               data=df)
summary(attgt)
ggdid(attgt)

agg.simple = aggte(attgt, type = "simple")
# summary(agg.simple)
print(paste("Simple Aggregation p-val:", 2 * pnorm(agg.simple$overall.att / agg.simple$overall.se)))

agg.es = aggte(attgt, type = "dynamic")
# summary(agg.es)
print(paste("Dynamic Aggregation p-val:", 2 * pnorm(agg.es$overall.att / agg.es$overall.se)))


## Specification (3) -- adding in Y^0
# covs = c("age", "size", "watchers", "lang", "forks", "license", "has_wiki", "y0_1", "y0_2", "y0_3", "y0_4")
covs = c("y0_3", "y0_4", "age", "size", "watchers")

## run Sant'Anna Callaway DID
attgt_3 = att_gt(yname = "ttc_d",
               tname = "time", 
               idname = "id", 
               gname = "first.treat", 
               xformla = reformulate(covs), 
               data=df)
summary(attgt_3)
ggdid(attgt_3)

agg.simple = aggte(attgt_3, type = "simple")
# summary(agg.simple)
print(paste("Simple Aggregation p-val:", 2 * pnorm(agg.simple$overall.att / agg.simple$overall.se)))

agg.es = aggte(attgt_3, type = "dynamic")
# summary(agg.es)
print(paste("Dynamic Aggregation p-val:", 2 * pnorm(agg.es$overall.att / agg.es$overall.se)))