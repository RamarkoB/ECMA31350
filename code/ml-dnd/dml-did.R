#The function DMLDiD returns the DMLDiD estimator and its estimated variance. 
#Data is randomly splitted into K=2 parts.
#To obtain a robust result, I repeat B=100 times and return the average of the 100 DMLDiD estimators. 
#Inputs:
#Y1: the outcome variable at t=1
#Y0: the outcome variable at t=0
#D: the treatment indicator
#p: the basis functions of control variables
#Trimming: I trim out the observations with propensity score value less than 0.05 and greater than 0.95

#Packages
library(glmnet)
library(randomForest)

#Algorithm

DMLDiD=function(Y1,Y0,D,p){
  N=length(Y1)
  B=100
  set.seed(123)
  random=sample(1:1000,B)
  
  thetabar=c(0)
  for (l in 1:B){
    k=2
    samplesplit=function(k,N){
      c1=1:N
      smp_size <- floor((1/k) * length(c1))
      
      ## set the seed to make your partition reproducible
      set.seed(random[l])
      train_ind <- sample(seq_len(length(c1)), size = smp_size)
      
      k1 <- c1[train_ind]
      k2 <- c1[-train_ind]
      return(rbind(k1,k2))
    }
    K=samplesplit(k,N)
    
    thetaDML=c(0)
    
    for (q in 1:k){
      ##Trimming
      set.seed(333)
      CV=cv.glmnet(p[-K[q,],],D[-K[q,]],family="binomial",alpha=1)
      fit=glmnet(p[-K[q,],],D[-K[q,]],family="binomial",alpha=1,lambda=CV$lambda.1se)
      beta1hat=fit$beta
      beta1hat <- as.numeric(as.character(beta1hat))
      
      ghat=1/(1+exp(-p[K[q,],]%*%beta1hat))
      
      index1=K[q,][which(ghat<0.9 & ghat>0.1)]
      
      ##Estimation
      ghat=1/(1+exp(-p[index1,]%*%beta1hat))
      
      index=which(D[-K[q,]]==0)
      y=Y1[-K[q,]]-Y0[-K[q,]]
      y=y[index]
      XX=X[-K[q,],]
      XX=XX[index,]
      
      model=randomForest(XX,y)
      ellhat=predict(model,X[index1,])
      
      thetaDML[q]=mean((Y1[index1]-Y0[index1])/mean(D[index1])*(D[index1]-ghat)/(1-ghat)-(D[index1]-ghat)/mean(D[index1])/(1-ghat)*ellhat)
      
    }
    
    thetabar[l]=mean(thetaDML)
    
    
  }
  finaltheta=mean(thetabar)
  finaltheta
  
  #Variance
  var=c(0)
  for (m in 1:B){
    k=2
    samplesplit=function(k,N){
      c1=1:N
      smp_size <- floor((1/k) * length(c1))
      
      ## set the seed to make your partition reproducible
      set.seed(random[m])
      train_ind <- sample(seq_len(length(c1)), size = smp_size)
      
      k1 <- c1[train_ind]
      k2 <- c1[-train_ind]
      return(rbind(k1,k2))
    }
    K=samplesplit(k,N)
    
    varDML=c(0)
    for (q in 1:k){
      ##Trimming
      set.seed(333)
      CV=cv.glmnet(p[-K[q,],],D[-K[q,]],family="binomial",alpha=1)
      fit=glmnet(p[-K[q,],],D[-K[q,]],family="binomial",alpha=1,lambda=CV$lambda.1se)
      beta1hat=fit$beta
      beta1hat <- as.numeric(as.character(beta1hat))
      
      ghat=1/(1+exp(-p[K[q,],]%*%beta1hat))
      
      index1=K[q,][which(ghat<0.9 & ghat>0.1)]
      
      
      ##Estimation
      ghat=1/(1+exp(-p[index1,]%*%beta1hat))
      
      index=which(D[-K[q,]]==0)
      y=Y1[-K[q,]]-Y0[-K[q,]]
      y=y[index]
      XX=X[-K[q,],]
      XX=XX[index,]
      
      
      model=randomForest(XX,y)
      ellhat=predict(model,X[index1,])
      
      G=-finaltheta/mean(D[index1])
      
      s=(Y1[index1]-Y0[index1])/mean(D[index1])*(D[index1]-ghat)/(1-ghat)-(D[index1]-ghat)/mean(D[index1])/(1-ghat)*ellhat-finaltheta+G*(D[index1]-mean(D[index1]))
      # test = (Y1[index1]-Y0[index1])/mean(D[index1])*(D[index1]-ghat)/(1-ghat)
      # test2 = (D[index1]-ghat)/mean(D[index1])/(1-ghat)*ellhat
      # test3 = finaltheta+G*(D[index1]-mean(D[index1]))
      # s = test - test2 - test3
      varDML[q]=mean(s^2)
    }
    
    var[m]=mean(varDML)
  }
  
  sd=sqrt(mean(var))/sqrt(N)
  return(c(finaltheta,sd))
}

## load in data
df = read.csv(here("data", "did-data-wide.csv"))[-1,]

# covs = c("age", "size", "watchers", "lang", "forks", "license", "has_wiki", "y0_1", "y0_2", "y0_3", "y0_4")
Y1 = df$ttc_d1
Y0 = df$ttc_d0
D = df$treat
# X = as.matrix(cbind(df$ttc_d0, df$age, df$size, df$watchers))
X = as.matrix(cbind(df$ttc_d0, df$age))

results = DMLDiD(Y1,Y0,D,X)
est = results[1]
se = results[2]

print(paste("est:", est, "se:", se, "pval:", 2 * pnorm(est / se)))
