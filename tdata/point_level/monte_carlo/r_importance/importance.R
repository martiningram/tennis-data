importance <- function(point_x, point_y, game_x, game_y, 
	set_x, set_y, tiebreak = FALSE, bestof3 = FALSE){

	point_importance <- function(serve, return, tiebreak = FALSE){
		
		win <- ifelse(tiebreak, 7, 4)
		
		if(tiebreak) outcomes <- tb_outcomes

		if(!((serve == (win-1) & return == win) | (serve == win & return == (win - 1))))
			outcomes$importance[outcomes$serve == serve & outcomes$return == return]
		else{
				outcomes$importance[outcomes$serve == (serve - 1)  & outcomes$return == (return - 1)]
		}
		
	}
	
	set_importance <- function(x, y, bestof3 = TRUE){
	
		prob3 <- matrix( c(.5, .5, .5, 1), 2, 2, byrow = TRUE)
		prob5 <- matrix( c(.38, .38, .25, .38, .5, .5, .25, .5, 1), 3, 3, byrow = TRUE)
		
		if(bestof3){
			if(x > 1) x <- 1
			if(y > 1) y <- 1
				prob3[x+1,y+1]
		}
		else{
			if(x > 2) x <- 2
			if(y > 2) y <- 2
				prob5[x+1, y+1]
		}
	}
	
	game_importance <- function(x, y){	
		m <- matrix( c(.3, .3, .18, .14, .03, .01, NA,
			.3, .33, .33, .17, .12, .01, NA,
			.3, .33, .37, .37, .14, .08, NA,
			.14,.32, .37,.42,.42, .09, NA,
			.1, .12, .36, .42, .5, .5, NA,
			.01, .06, .08, .41, .5, .5,.5,
			NA, NA, NA, NA, NA, .5, 1
		), 7, 7, byrow = TRUE)
		
		if(x > 6) x <- 6
		if(y > 6) y <- 6
		
	m[x+1, y+1]
	}
		
point_importance(point_x, point_y, tiebreak) * game_importance(game_x, game_y) *
			set_importance(set_x, set_y, bestof3)				
}
