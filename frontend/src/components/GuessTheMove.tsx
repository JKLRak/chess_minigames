import { useState, useCallback, useRef, useEffect } from 'react';
import { ChessBoard } from './ChessBoard';
import { TrophyIcon, FlameIcon, BrainIcon, CheckIcon, CrossIcon, RotateIcon } from './Icons';
import { type MovePuzzle, type MoveAnswerResult, getMovePuzzle, submitMoveAnswer } from '../api';
import { formatMove } from '../utils/fen';

interface GuessTheMoveProps {
    onBack: () => void;
}

export function GuessTheMove({ onBack }: GuessTheMoveProps) {
    const [puzzle, setPuzzle] = useState<MovePuzzle | null>(null);
    const [result, setResult] = useState<MoveAnswerResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [currentStreak, setCurrentStreak] = useState(0);
    const [longestStreak, setLongestStreak] = useState<number>(() => {
        try {
            const saved = localStorage.getItem('guess_move_longest_streak');
            return saved ? parseInt(saved, 10) || 0 : 0;
        } catch {
            return 0;
        }
    });
    const [isNewBest, setIsNewBest] = useState(false);
    const [chosenMove, setChosenMove] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const nextTimerRef = useRef<number | null>(null);

    useEffect(() => {
        return () => {
            if (nextTimerRef.current) clearTimeout(nextTimerRef.current);
        };
    }, []);

    const fetchPuzzle = useCallback(async () => {
        setLoading(true);
        setResult(null);
        setChosenMove(null);
        setError(null);
        try {
            const data = await getMovePuzzle();
            setPuzzle(data);
        } catch (e) {
            console.error(e);
            setError('Error loading puzzle. Please try again.');
        } finally {
            setLoading(false);
        }
    }, []);

    const submitAnswer = async (move: string) => {
        if (!puzzle || result) return;
        setChosenMove(move);
        setLoading(true);
        setError(null);
        try {
            const data = await submitMoveAnswer(puzzle.puzzle_id, move);
            setResult(data);

            if (data.correct) {
                const nextStreak = currentStreak + 1;
                setCurrentStreak(nextStreak);
                if (nextStreak > longestStreak) {
                    setLongestStreak(nextStreak);
                    setIsNewBest(true);
                    try {
                        localStorage.setItem('guess_move_longest_streak', nextStreak.toString());
                    } catch {}
                }
                // Automatically advance to next puzzle after the success overlay displays (~0.6s)
                nextTimerRef.current = window.setTimeout(() => {
                    setIsNewBest(false);
                    fetchPuzzle();
                }, 600);
            }
        } catch (e) {
            console.error(e);
            setChosenMove(null);
            setError('Submission failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const restartGame = () => {
        if (nextTimerRef.current) clearTimeout(nextTimerRef.current);
        setCurrentStreak(0);
        setIsNewBest(false);
        setResult(null);
        setChosenMove(null);
        setError(null);
        fetchPuzzle();
    };

    const handleBack = () => {
        if (nextTimerRef.current) clearTimeout(nextTimerRef.current);
        onBack();
    };

    const isGameOver = result !== null && !result.correct;

    return (
        <div className="guess-move-container">
            <button className="back-btn" onClick={handleBack} id="guess-move-back">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
                Back
            </button>

            {!puzzle ? (
                <div className="guess-move-start">
                    <div className="hero-icon-container">
                        <BrainIcon size={56} />
                    </div>
                    <h2>Guess the Move</h2>
                    <p className="guess-move-subtitle">
                        Positions from games rated <strong>2000+</strong>.<br />
                        How many moves can you guess in a row?
                    </p>
                    {longestStreak > 0 && (
                        <div className="start-best-banner">
                            <TrophyIcon size={16} />
                            <span>Personal Best Streak: <strong>{longestStreak}</strong></span>
                        </div>
                    )}
                    <button
                        className="start-gauntlet-btn"
                        onClick={fetchPuzzle}
                        disabled={loading}
                        id="guess-move-start-btn"
                    >
                        {loading ? 'Finding a game...' : (
                            <>
                                <span>Start Guessing</span>
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="none">
                                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                                </svg>
                            </>
                        )}
                    </button>
                    {error && (
                        <div className="move-result incorrect" style={{ marginTop: '1.5rem' }}>
                            <span>⚠️</span>
                            <span>{error}</span>
                        </div>
                    )}
                </div>
            ) : isGameOver ? (
                /* ========================================================== */
                /* Game End / Game Over View                                  */
                /* ========================================================== */
                <div className="game-over-view">
                    <div className="game-over-banner">
                        <div className="game-over-icon-wrapper">
                            <CrossIcon size={32} />
                        </div>
                        <h2>Streak Ended</h2>
                        <p className="game-over-subtitle">
                            {currentStreak > 0
                                ? `You found ${currentStreak} master move${currentStreak === 1 ? '' : 's'} in a row`
                                : 'Try again to start a new streak'}
                        </p>
                    </div>

                    {/* Stats Grid */}
                    <div className="game-over-stats-grid">
                        <div className="game-over-stat-card">
                            <span className="stat-label">Final Streak</span>
                            <span className="stat-value final-val">{currentStreak}</span>
                        </div>
                        <div className="game-over-stat-card">
                            <span className="stat-label">Longest Streak</span>
                            <span className="stat-value best-val">{longestStreak}</span>
                        </div>
                    </div>

                    {isNewBest && (
                        <div className="new-record-pill">
                            <TrophyIcon size={15} />
                            <span>New Personal Best!</span>
                        </div>
                    )}

                    {/* Move Comparison */}
                    <div className="game-over-reveal">
                        <div className="reveal-box">
                            <span className="reveal-label">Your guess</span>
                            <span className="reveal-move incorrect-move">
                                {result.chosen_move}
                                <CrossIcon size={14} />
                            </span>
                        </div>
                        <div className="reveal-divider">vs</div>
                        <div className="reveal-box">
                            <span className="reveal-label">Master played</span>
                            <span className="reveal-move correct-move">
                                {result.correct_move}
                                <CheckIcon size={14} />
                            </span>
                        </div>
                    </div>

                    {/* Board Preview of the position */}
                    <div className="board-section">
                        <ChessBoard
                            fen={puzzle.fen}
                            hiddenSquares={[]}
                            userAnswers={{}}
                            onAnswerChange={() => {}}
                            flipped={puzzle.side_to_move === 'black'}
                        />
                    </div>

                    {/* Game Source Details */}
                    {result.game_info && (
                        <div className="game-info">
                            <p>
                                Game: <strong>{result.game_info.white}</strong> ({result.game_info.white_elo || '?'}) vs <strong>{result.game_info.black}</strong> ({result.game_info.black_elo || '?'})
                            </p>
                            {result.game_info.ply > 0 && (
                                <p>Position {formatMove(result.game_info.ply)}</p>
                            )}
                            {result.game_info.url && (
                                <a
                                    href={result.game_info.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    View Game ↗
                                </a>
                            )}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="game-over-actions">
                        <button
                            className="btn primary restart-btn"
                            onClick={restartGame}
                            disabled={loading}
                            id="play-again-btn"
                        >
                            <RotateIcon size={18} />
                            <span>{loading ? 'Starting...' : 'Play Again'}</span>
                        </button>
                    </div>
                </div>
            ) : (
                /* ========================================================== */
                /* In-Game Active Puzzle View                                 */
                /* ========================================================== */
                <div className="guess-move-game">
                    {/* Streak Tracker */}
                    <div className="streak-tracker" id="streak-tracker">
                        <div className="streak-badge current">
                            <FlameIcon size={18} className="streak-fire-svg" />
                            <span className="streak-text">
                                Streak: <strong>{currentStreak}</strong>
                            </span>
                        </div>
                        <span className="streak-divider">•</span>
                        <div className="streak-badge best">
                            <TrophyIcon size={16} className="streak-trophy-svg" />
                            <span className="streak-text">
                                Best: <strong>{longestStreak}</strong>
                            </span>
                        </div>
                    </div>

                    {/* Side to move indicator */}
                    <div className={`side-to-move ${puzzle.side_to_move}`}>
                        <span className="side-dot"></span>
                        {puzzle.side_to_move === 'white' ? 'White' : 'Black'} to move
                    </div>

                    {/* Board */}
                    <div className="board-section">
                        <ChessBoard
                            fen={puzzle.fen}
                            hiddenSquares={[]}
                            userAnswers={{}}
                            onAnswerChange={() => {}}
                            flipped={puzzle.side_to_move === 'black'}
                        />
                        {/* Success Green Overlay directly over the chessboard */}
                        {result && result.correct && (
                            <div className="board-success-overlay" id="board-success-overlay">
                                <div className="success-overlay-content">
                                    <div className="success-overlay-icon-box">
                                        <CheckIcon size={36} />
                                    </div>
                                    <div className="success-overlay-text">Correct!</div>
                                    {currentStreak > 1 && (
                                        <div className="success-overlay-sub">
                                            <span>{currentStreak} in a row</span>
                                            <FlameIcon size={16} />
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Move Options */}
                    <div className="move-options">
                        <button
                            className={`move-btn ${
                                result
                                    ? chosenMove === puzzle.move_a
                                        ? result.correct_move === puzzle.move_a
                                            ? 'correct'
                                            : 'incorrect'
                                        : result.correct_move === puzzle.move_a
                                            ? 'correct reveal'
                                            : ''
                                    : ''
                            }`}
                            onClick={() => submitAnswer(puzzle.move_a)}
                            disabled={!!result || loading}
                            id="move-option-a"
                        >
                            <span className="move-san">{puzzle.move_a}</span>
                        </button>

                        <span className="move-or">or</span>

                        <button
                            className={`move-btn ${
                                result
                                    ? chosenMove === puzzle.move_b
                                        ? result.correct_move === puzzle.move_b
                                            ? 'correct'
                                            : 'incorrect'
                                        : result.correct_move === puzzle.move_b
                                            ? 'correct reveal'
                                            : ''
                                    : ''
                            }`}
                            onClick={() => submitAnswer(puzzle.move_b)}
                            disabled={!!result || loading}
                            id="move-option-b"
                        >
                            <span className="move-san">{puzzle.move_b}</span>
                        </button>
                    </div>

                    {/* Error Feedback */}
                    {error && (
                        <div className="move-result incorrect" style={{ marginTop: '1rem' }}>
                            <span>⚠️</span>
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Result Feedback Flash */}
                    {result && result.correct && (
                        <div className="move-result correct">
                            <span>✓</span>
                            <span>Correct!</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
