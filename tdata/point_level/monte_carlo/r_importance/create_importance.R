# All credit for this code goes to Stephanie Kovalchik.

# Importance matrices
game_win <- function(p = .64, serve, return, tiebreak = FALSE){
		
		win <- ifelse(tiebreak, 7, 4)
		deuce <- ifelse(tiebreak, 6, 3)
		before_deuce <- deuce - 1
		
		if(serve == win){
			if(return <= before_deuce)
				return(1)
			else
				return(p + (1-p) *p^2 / (1 - 2*p*(1-p)))
		}
		else if(return == win){
			if(serve <= 2)
				return(0)
			else
				return(p*p^2 / (1 - 2*p*(1-p)))
		}
		else{
			if(return < deuce){
				p_nodeuce <- sapply(return:before_deuce, function(y) p*dbinom((deuce-serve),((y-return)+(deuce-serve)), 
					prob = p))
			}
			else{
				p_nodeuce <- 0
			}
		p_deuce <- dbinom((deuce-serve),((deuce-serve) + (deuce-return)), prob = p) * p^2 / (1 - 2*p*(1-p))
	
	return(sum(p_nodeuce) + p_deuce)
	}
}

m <- matrix(0, 4, 4)

serve_score <- as.vector(row(m) - 1)
return_score <- as.vector(col(m) - 1)

outcomes <- data.frame(
	serve = serve_score,
	return = return_score
)

outcomes$importance <- apply(outcomes, 1, 
	 function(x) game_win(serve=x[1]+1,return = x[2]) - game_win(serve=x[1], return = x[2] + 1))


m <- matrix(0, 7, 7)

serve_score <- as.vector(row(m) - 1)
return_score <- as.vector(col(m) - 1)

tb_outcomes <- data.frame(
	serve = serve_score,
	return = return_score
)

# Assume tiebreak neutralizes serve
tb_outcomes$importance <- apply(tb_outcomes, 1, 
	 function(x) game_win(p = .5, serve=x[1]+1,return = x[2], 
	 tiebreak = TRUE) - game_win(p = .5, serve=x[1], return = x[2] + 1, tiebreak = TRUE))
	 
tb_outcomes$importance[tb_outcomes$return == 6]	 <- tb_outcomes$importance[tb_outcomes$serve == 6]

#save(tb_outcomes, outcomes, file = "./importance.RData")
