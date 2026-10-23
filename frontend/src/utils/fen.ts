export function fenToGrid(fen: string): { piece: string, square: string }[] {
    const grid: { piece: string, square: string }[] = [];
    const pos = fen.split(' ')[0];
    let rank = 7;
    let file = 0;
    
    for (let i = 0; i < pos.length; i++) {
        const c = pos[i];
        if (c === '/') {
            rank--;
            file = 0;
        } else if (c >= '1' && c <= '8') {
            const emptyCount = parseInt(c, 10);
            for (let j = 0; j < emptyCount; j++) {
                grid.push({ piece: '', square: squareIdentifier(rank, file) });
                file++;
            }
        } else {
            grid.push({ piece: c, square: squareIdentifier(rank, file) });
            file++;
        }
    }
    return grid;
}

export function squareIdentifier(rank: number, file: number): string {
    return String.fromCharCode('a'.charCodeAt(0) + file) + (rank + 1).toString();
}

export function pieceToSvg(piece: string): string {
    if (!piece) return '';
    const color = piece === piece.toUpperCase() ? 'w' : 'b';
    const type = piece.toUpperCase();
    return `/pieces/${color}${type}.svg`;
}

export function formatMove(ply: number): string {
    if (ply === 0) return "at the starting position";
    const moveNum = Math.ceil(ply / 2);
    const color = ply % 2 === 1 ? "White's" : "Black's";
    const getOrdinal = (n: number) => {
        const j = n % 10, k = n % 100;
        if (j === 1 && k !== 11) return n + "st";
        if (j === 2 && k !== 12) return n + "nd";
        if (j === 3 && k !== 13) return n + "rd";
        return n + "th";
    };
    return `after ${color} ${getOrdinal(moveNum)} move`;
}
