import { pieceToSvg } from '../utils/fen';

interface PieceSelectorProps {
    onSelect: (piece: string) => void;
}

export function PieceSelector({ onSelect }: PieceSelectorProps) {
    const pieces = [
        ['P', 'N', 'B', 'R', 'Q'],
        ['p', 'n', 'b', 'r', 'q']
    ];

    return (
        <div className="piece-selector">
            <button className="empty-btn" onClick={() => onSelect('')}>Empty Square</button>
            <div className="piece-grid">
                {pieces.map((row, i) => (
                    <div key={i} className="piece-row">
                        {row.map(p => (
                            <button
                                key={p}
                                className="piece-btn"
                                onClick={() => onSelect(p)}
                            >
                                <img src={pieceToSvg(p)} alt={p} className="piece-selector-img" draggable={false} />
                            </button>
                        ))}
                    </div>
                ))}
            </div>
        </div>
    );
}
