export type AuctionStatus =
  | 'draft'
  | 'review'
  | 'rejected'
  | 'open'
  | 'closed'
  | 'paused';

export interface User {
  id: number;
  username: string;
  can_moderate: boolean;
  is_admin?: boolean;
}

export interface Category {
  id: number;
  name: string;
}

export interface Auction {
  id: number;
  owner_id: number;
  category: number;
  title: string;
  description: string;
  budget_kopecks: number;
  ends_at: string;
  due_at: string;
  status: AuctionStatus;
  moderation_reason: string;
  winner_id: number | null;
  winner_username: string | null;
  winner_rating: number | null;
  winner_reviews_count: number;
  payment_kopecks: number | null;
  closed_at: string | null;
}

export interface Bid {
  id: number;
  auction_id: number;
  bidder_id?: number;
  bidder_username?: string;
  bidder_rating?: number | null;
  bidder_reviews_count?: number;
  amount_kopecks: number;
  created_at: string;
}

export interface Review {
  id: number;
  auction_id: number;
  auction_title: string;
  reviewer_username: string;
  performer_id: number;
  rating: number;
  comment: string;
  created_at: string;
}

export interface PerformerReputation {
  performer: { id: number; username: string };
  average_rating: number | null;
  reviews_count: number;
  completed_tasks_count: number;
  wins_count: number;
  rating_distribution: Record<string, number>;
  reviews: Review[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AuctionFilters {
  mine?: boolean;
  status?: AuctionStatus;
  category?: number;
  search?: string;
  page?: number;
}

export interface AuctionCreatePayload {
  category: number;
  title: string;
  description: string;
  budget_kopecks: number;
  ends_at: string;
  due_at: string;
}

export type AuctionPatchPayload = Partial<AuctionCreatePayload>;
