import { useState } from 'react';
import { ChessBoard } from './components/ChessBoard';
import { GuessTheMove } from './components/GuessTheMove';
import { SwordsIcon, BrainIcon } from './components/Icons';
import { type Puzzle, type DailyStats, getDailyToday, submitDailyGuess, getDailyStats as fetchDailyStats } from './api';
import { formatMove } from './utils/fen';

type AppMode = 'home' | 'gauntlet' | 'guess-move';

export default function App() {
    const [mode, setMode] = useState<AppMode>('home');
    const [gauntlet, setGauntlet] = useState<Puzzle[] | null>(null);
    const [currentLevel, setCurrentLevel] = useState<number>(1);
    
    const [userAnswers, setUserAnswers] = useState<Record<string, string>>({});
    const [actualAnswers, setActualAnswers] = useState<Record<string, string> | null>(null);
    const [results, setResults] = useState<Record<string, boolean> | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    // Global End Stats
    const [finalStats, setFinalStats] = useState<DailyStats | null>(null);
    
    const puzzle = gauntlet ? gauntlet.find(p => p.level === currentLevel) : null;
    const isSubmitted = actualAnswers !== null;
    
    const startGauntlet = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getDailyToday();
            setGauntlet(data.gauntlet);
            setCurrentLevel(1);
            resetLevelState();
            setFinalStats(null);
        } catch (e) {
            console.error(e);
            setError("Error loading gauntlet. Please check backend connection and try again.");
        } finally {
            setLoading(false);
        }
    };
    
    const resetLevelState = () => {
        setUserAnswers({});
        setActualAnswers(null);
        setResults(null);
        setError(null);
    }
    
    const nextLevel = () => {
        if (currentLevel < 4) {
            setCurrentLevel(currentLevel + 1);
            resetLevelState();
        }
    }

    const finishGauntlet = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchDailyStats();
            setFinalStats(data);
            setCurrentLevel(5); // Mode 5 is "Final Stats Screen"
        } catch (e) {
            console.error(e);
            setError("Error fetching final stats. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleAnswerChange = (square: string, piece: string) => {
        if (piece) {
            setUserAnswers(prev => ({ ...prev, [square]: piece }));
        } else {
            const newAnswers = { ...userAnswers };
            delete newAnswers[square];
            setUserAnswers(newAnswers);
        }
    };

    const submitAnswer = async () => {
        if (!puzzle) return;
        setLoading(true);
        setError(null);
        try {
            const data = await submitDailyGuess(currentLevel, userAnswers);
            setResults(data.results);
            setActualAnswers(data.actual_answers);
        } catch (e) {
            console.error(e);
            setError("Submission failed. Please check connection and try again.");
        } finally {
            setLoading(false);
        }
    };

    const getScore = () => {
        if (!results) return 0;
        return Object.values(results).filter(Boolean).length;
    };

    const goHome = () => {
        setMode('home');
        setGauntlet(null);
        resetLevelState();
        setFinalStats(null);
    };

    // =======================================================================
    // RENDER
    // =======================================================================

    if (mode === 'guess-move') {
        return (
            <div className="app-container">
                <header className="header">
                    <h1>Chess Puzzles</h1>
                </header>
                <GuessTheMove onBack={goHome} />
            </div>
        );
    }

    if (mode === 'gauntlet') {
        return (
            <div className="app-container">
                <header className="header">
                    <h1>Chess Daily Gauntlet</h1>
                    <p>Can you guess missing pieces in today's active games?</p>
                </header>

                <button className="back-btn" onClick={goHome} id="gauntlet-back">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M19 12H5M12 19l-7-7 7-7" />
                    </svg>
                    Back
                </button>

                {!gauntlet ? (
                    <div className="start-screen">
                        <div className="hero-icon-container">
                            <SwordsIcon size={56} />
                        </div>
                        <button 
                            className="start-gauntlet-btn" 
                            onClick={startGauntlet}
                            disabled={loading}
                        >
                            {loading ? 'Preparing Battle...' : (
                                <>
                                    <span>Start Daily Gauntlet</span>
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="none">
                                        <polygon points="5 3 19 12 5 21 5 3"></polygon>
                                    </svg>
                                </>
                            )}
                        </button>
                        <p style={{marginTop: '30px', color: 'var(--text-secondary)', fontSize: '1.2rem', lineHeight: '1.6'}}>
                            4 intense levels of missing pieces. <br/>See how you stack up against the global audience!
                        </p>
                        {error && (
                            <div className="move-result incorrect" style={{ marginTop: '20px' }}>
                                <span>⚠️</span>
                                <span>{error}</span>
                            </div>
                        )}
                    </div>
                ) : currentLevel === 5 && finalStats ? (
                    <div className="stats-screen">
                        <div className="stats-card">
                            <h2>Gauntlet Completed!</h2>
                            <h3 className="stats-score-headline">
                                You scored {finalStats.user_total} / 10 correct pieces!
                            </h3>
                            
                            <div className="stats-distribution-panel">
                                <h4 className="stats-distribution-title">Global Score Distribution</h4>
                                <div className="bar-graph">
                                    {[...Array(11)].map((_, score) => {
                                        const maxCount = Math.max(...Object.values(finalStats.distribution).map(v => Number(v)), 1);
                                        const count = finalStats.distribution[score] || 0;
                                        const barPercentage = (count / maxCount) * 100;
                                        const totalPercentage = finalStats.total_players > 0 
                                            ? Math.round((count / finalStats.total_players) * 100) 
                                             : 0;
                                        
                                        const isUserScore = score === finalStats.user_total;
                                        
                                        return (
                                            <div key={score} className="bar-row">
                                                <div className="bar-label">{score}</div>
                                                <div className="bar-track">
                                                    <div
                                                        className={`bar-fill ${isUserScore ? 'user-score' : 'other-score'}`}
                                                        style={{ width: `${barPercentage}%` }}
                                                    ></div>
                                                </div>
                                                <div className="bar-pct">{totalPercentage}%</div>
                                            </div>
                                        );
                                    })}
                                </div>
                                <p className="stats-caption">
                                    Based on {finalStats.total_players} players who finished today's gauntlet.
                                </p>
                            </div>

                            <button className="btn secondary" style={{marginTop: '30px'}} onClick={goHome}>
                                Back to Home
                            </button>
                        </div>
                    </div>
                ) : puzzle ? (
                    <div className="game-screen">
                        <div className="level-bar">
                            <h2>Level {currentLevel} of 4</h2>
                        </div>
                        
                        <div className="board-section">
                            <ChessBoard 
                                fen={puzzle.fen}
                                hiddenSquares={puzzle.hidden_squares}
                                userAnswers={userAnswers}
                                actualAnswers={actualAnswers || undefined}
                                results={results || undefined}
                                onAnswerChange={handleAnswerChange}
                            />
                        </div>
                        
                        <div className="controls">
                            {isSubmitted ? (
                                <div className="results">
                                    <h3>Score: {getScore()} / {puzzle.hidden_squares.length}</h3>
                                    <div className="incorrect-guesses">
                                        {puzzle.hidden_squares.map(sq => (
                                            !results![sq] && (
                                                <span key={sq} className="incorrect-badge">
                                                    ✗ {sq}
                                                </span>
                                            )
                                        ))}
                                    </div>
                                    <div className="game-info">
                                        <p>Game: {puzzle.game_info.white} vs {puzzle.game_info.black}</p>
                                        <p>Position {formatMove(puzzle.game_info.ply)}</p>
                                        <a href={puzzle.game_info.url} target="_blank" rel="noopener noreferrer">
                                            View Game
                                        </a>
                                    </div>
                                    
                                    {currentLevel < 4 ? (
                                        <button className="btn primary" onClick={nextLevel}>Next Level</button>
                                    ) : (
                                        <button className="btn secondary" onClick={finishGauntlet}>
                                            {loading ? 'Crunching Stats...' : 'View Final Results'}
                                        </button>
                                    )}
                                </div>
                            ) : (
                                <div className="game-status">
                                    <p>{puzzle.hidden_squares.length} pieces hidden</p>
                                    <button className="btn primary" onClick={submitAnswer} disabled={loading}>
                                        {loading ? 'Evaluating...' : 'Check Answer'}
                                    </button>
                                    {error && (
                                        <p style={{ color: '#f87171', marginTop: '10px', fontSize: '0.9rem' }}>
                                            ⚠️ {error}
                                        </p>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                ) : null}
            </div>
        );
    }

    // =======================================================================
    // HOME SCREEN
    // =======================================================================
    return (
        <div className="app-container">
            <header className="header">
                <h1>Chess Puzzles</h1>
                <p>Test your chess intuition with puzzles from real games</p>
            </header>

            <div className="home-grid">
                <button
                    className="mode-card"
                    onClick={() => setMode('gauntlet')}
                    id="mode-gauntlet"
                >
                    <div className="mode-card-icon-wrapper">
                        <SwordsIcon size={28} />
                    </div>
                    <h2>Daily Gauntlet</h2>
                    <p>Guess missing pieces across 4 levels. One challenge per day — compare with others!</p>
                    <span className="mode-card-tag">Daily</span>
                </button>

                <button
                    className="mode-card accent"
                    onClick={() => setMode('guess-move')}
                    id="mode-guess-move"
                >
                    <div className="mode-card-icon-wrapper">
                        <BrainIcon size={28} />
                    </div>
                    <h2>Guess the Move</h2>
                    <p>See a position from a 2000+ Elo game. Pick the move that was actually played!</p>
                    <span className="mode-card-tag">Unlimited</span>
                </button>
            </div>
        </div>
    );
}
