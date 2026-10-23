export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export interface MoveGameInfo {
    id: string;
    url: string;
    white: string;
    black: string;
    white_elo: number;
    black_elo: number;
    result: string;
    ply: number;
}

export interface GauntletGameInfo {
    id: string;
    url: string;
    white: string;
    black: string;
    result?: string;
    ply: number;
}

export interface Puzzle {
    level: number;
    fen: string;
    hidden_squares: string[];
    game_info: GauntletGameInfo;
}

export interface DailyTodayResponse {
    date: string;
    gauntlet: Puzzle[];
}

export interface DailyGuessResponse {
    score: number;
    max_score: number;
    results: Record<string, boolean>;
    actual_answers: Record<string, string>;
    already_submitted?: boolean;
}

export interface DailyStats {
    user_total: number;
    total_players: number;
    distribution: Record<number, number>;
}

export interface MovePuzzle {
    puzzle_id: string;
    fen: string;
    side_to_move: 'white' | 'black';
    move_a: string;
    move_b: string;
}

export interface MoveAnswerResult {
    correct: boolean;
    correct_move: string;
    chosen_move: string;
    game_info?: MoveGameInfo;
}

export async function getDailyToday(): Promise<DailyTodayResponse> {
    const res = await fetch(`${API_URL}/daily/today`);
    if (!res.ok) {
        throw new Error('Failed to fetch daily gauntlet');
    }
    return res.json();
}

export async function submitDailyGuess(level: number, userAnswers: Record<string, string>): Promise<DailyGuessResponse> {
    const res = await fetch(`${API_URL}/daily/today/guess/${level}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userAnswers),
    });
    if (!res.ok) {
        throw new Error('Failed to submit daily guess');
    }
    return res.json();
}

export async function getDailyStats(): Promise<DailyStats> {
    const res = await fetch(`${API_URL}/daily/today/stats`);
    if (!res.ok) {
        throw new Error('Failed to fetch daily stats');
    }
    return res.json();
}

export async function getMovePuzzle(): Promise<MovePuzzle> {
    const res = await fetch(`${API_URL}/move-guess/puzzle`);
    if (!res.ok) {
        throw new Error('Failed to fetch move puzzle');
    }
    return res.json();
}

export async function submitMoveAnswer(puzzleId: string, chosenMove: string): Promise<MoveAnswerResult> {
    const res = await fetch(`${API_URL}/move-guess/answer/${puzzleId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chosen_move: chosenMove }),
    });
    if (!res.ok) {
        throw new Error('Failed to submit move answer');
    }
    return res.json();
}
