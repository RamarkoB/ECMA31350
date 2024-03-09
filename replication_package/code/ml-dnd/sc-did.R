library(did)

## Extract coefficients out of att_gt object
attgt_coefs <- function(attgt, label) {
  cv <- qnorm(1 - .05 / 2) # 95% confidence interval
  cilb <- attgt$att - cv * attgt$se
  ciub <- attgt$att + cv * attgt$se
  df <- data.frame(year = c(1:9), coef = attgt$att, cilb =
                     cilb, ciub = ciub, label = label)
  return(df)
}

## Base function for running evaluating att_gt result
eval_attgt <- function(attgt) {
  summary(attgt)
  # ggdid(attgt)
  
  agg.simple = aggte(attgt, type = "simple")
  pval.simple = 2 * pnorm(agg.simple$overall.att / agg.simple$overall.se)
  
  agg.es = aggte(attgt, type = "dynamic")
  pval.es = 2 * pnorm(agg.es$overall.att / agg.es$overall.se)
  
  if (pval.simple < pval.es) {
    print(paste("Simple Aggregation est:", agg.simple$overall.att, 
                "se:", agg.es$overall.se,
                "pval:", pval.simple))
  } else {
    print(paste("Dynamic Aggregation est:", agg.es$overall.att, 
                "se:", agg.es$overall.se, 
                "pval:", pval.es))
  }
}

## Specification (2) -- only pre-treatment covariates
sc_did_2 <- function(df) {
  df$first.treat = df$treat * 5
  df$has_wiki = ifelse(df$has_wiki == "True", 1, 0)
  
  # covs = c("age", "size", "watchers", "lang", "forks", "license", "has_wiki")
  covs = c("age", "size", "watchers", "count")
  
  ## run Sant'Anna Callaway DID
  attgt = att_gt(yname = "ttc_d",
                 tname = "time", 
                 idname = "id", 
                 gname = "first.treat", 
                 xformla = reformulate(covs),
                 allow_unbalanced_panel = TRUE,
                 base_period="universal",
                 data=df)
  
  eval_attgt(attgt)
  return(attgt_coefs(attgt, label="Spec (2)"))
}


## Specification (3) -- Adding in Y0
sc_did_3 <- function(df) {
  df$first.treat = df$treat * 5
  df$has_wiki = ifelse(df$has_wiki == "True", 1, 0)
  
  # covs = c("age", "size", "watchers", "lang", "forks", "license", "has_wiki", "y0_1", "y0_2", "y0_3", "y0_4")
  covs = c("y0_4", "age", "size", "watchers", "count")
  
  ## run Sant'Anna Callaway DID
  attgt = att_gt(yname = "ttc_d",
                 tname = "time", 
                 idname = "id", 
                 gname = "first.treat", 
                 xformla = reformulate(covs),
                 allow_unbalanced_panel = TRUE,
                 base_period="universal",
                 data=df)
  
  eval_attgt(attgt)
  return(attgt_coefs(attgt, label="Spec (3)"))
}

## DDML test
# load the ddml package
library(ddml)

# write a general wrapper for ddml_att
ddml_did_method <- function(y1, y0, D, covariates, ...) {
  # Compute difference in outcomes
  delta_y <- y1 - y0
  # Compute the ATT
  att_fit <- ddml_att(y = delta_y, D = D, X = covariates, ...)
  # Return results
  inf.func <- att_fit$psi_b + att_fit$att * att_fit$psi_a
  output <- list(ATT = att_fit$att, att.inf.func = inf.func)
  return(output)
}

my_did_xgboost <- function(y1, y0, D, covariates, ...) {
  # Hard-code learners
  learners = list(what = mdl_xgboost,
                  args = list(nround = 500,
                              params = list(eta = 0.2, max_depth = 1)))
                              # early_stopping_rounds = 1))
  learners_DX = learners

  # Call the general ddml_did method w/ additional hard-coded arguments
  ddml_did_method(y1, y0, D, covariates,
                  learners = learners,
                  learners_DX = learners_DX,
                  sample_folds = 10,
                  silent = TRUE)
}

sc_xgboost <- function(df) {
  df$first.treat = df$treat * 5
  df$has_wiki = ifelse(df$has_wiki == "True", 1, 0)
  covs = c("y0_4", "age", "size", "watchers")
  
  attgt_xgboost <- att_gt(yname = "ttc_d",
                          tname = "time",
                          idname = "id",
                          gname = "first.treat",
                          xformla = reformulate(covs),
                          data = df,
                          est_method = my_did_xgboost,
                          base_period = "universal")
  # allow_unbalanced_panel = TRUE)
  eval_attgt(attgt_xgboost)
  return(list(attgt_coefs(attgt_xgboost, label="Spec (5)"), attgt_xgboost))
}
