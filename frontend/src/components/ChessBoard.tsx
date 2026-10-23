import { useState } from 'react';
import { fenToGrid, pieceToSvg } from '../utils/fen';
import { PieceSelector } from './PieceSelector';

const RANKS = ['8', '7', '6', '5', '4', '3', '2', '1'];
const FILES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];

interface ChessBoardProps {
    fen: string;
    hiddenSquares: string[];
    userAnswers: Record<string, string>;
    onAnswerChange: (square: string, piece: string) => void;
    results?: Record<string, boolean>;
    actualAnswers?: Record<string, string>;
    flipped?: boolean;
}

export function ChessBoard({ fen, hiddenSquares, userAnswers, onAnswerChange, results, actualAnswers, flipped = false }: ChessBoardProps) {
    const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
    const grid = fenToGrid(fen);
    const displayedGrid = flipped ? [...grid].reverse() : grid;
    const ranks = flipped ? [...RANKS].reverse() : RANKS;
    const files = flipped ? [...FILES].reverse() : FILES;

    const handleSquareClick = (square: string) => {
        if (hiddenSquares.includes(square) && !actualAnswers) {
            setSelectedSquare(square);
        }
    };

    const handlePieceSelected = (piece: string) => {
        if (selectedSquare) {
            onAnswerChange(selectedSquare, piece);
        }
        setSelectedSquare(null);
    };

    return (
        <div className="board-container">
            <div className="board-wrapper">
                <div className="board-ranks" aria-hidden="true">
                    {ranks.map(r => (
                        <span key={r} className="board-coord">{r}</span>
                    ))}
                </div>
                <div className="chessboard">
                    {displayedGrid.map(cell => {
                        const isLight = (cell.square.charCodeAt(0) - 97 + parseInt(cell.square[1], 10)) % 2 === 0;
                        const isHidden = hiddenSquares.includes(cell.square);
                        const hasAnswer = !!userAnswers[cell.square];
                        
                        let contentString = '';
                        let squareClass = `square ${isLight ? 'light' : 'dark'}`;
                        
                        if (actualAnswers) {
                            // Challenge submitted
                            if (isHidden) {
                                const correct = results ? results[cell.square] : false;
                                squareClass += correct ? ' correct' : ' incorrect';
                                contentString = actualAnswers[cell.square] || '';
                            } else {
                                contentString = cell.piece || '';
                            }
                        } else if (isHidden) {
                            squareClass += ' hidden-square';
                            if (hasAnswer) {
                                contentString = userAnswers[cell.square];
                            }
                        } else {
                            contentString = cell.piece || '';
                        }

                        if (selectedSquare === cell.square) {
                            squareClass += ' selected';
                        }

                        return (
                            <div 
                                key={cell.square} 
                                className={squareClass}
                                onClick={() => handleSquareClick(cell.square)}
                            >
                                {contentString && (
                                    <img 
                                        src={pieceToSvg(contentString)} 
                                        alt={contentString} 
                                        className="piece-img" 
                                        draggable={false}
                                    />
                                )}
                            </div>
                        );
                    })}
                </div>
                <div className="board-files" aria-hidden="true">
                    {files.map(f => (
                        <span key={f} className="board-coord">{f}</span>
                    ))}
                </div>
            </div>
            
            {selectedSquare && (
                 <div className="selector-modal-overlay" onClick={() => setSelectedSquare(null)}>
                     <div className="selector-modal" onClick={e => e.stopPropagation()}>
                         <h3>What piece goes on {selectedSquare}?</h3>
                         <PieceSelector onSelect={handlePieceSelected} />
                     </div>
                 </div>
            )}
        </div>
    );
}
