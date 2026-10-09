export interface JobMatch {
  id: string | number | null;
  job_id: string | null;
  title: string | null;
  company: string | null;
  url: string | null;
  salary: string | null;
  location: string | null;
  working_model: string | null;
  experience: string | null;
  description: string | null;
  requirements: string | null;
  benefits: string | null;
  cv_name: string | null;
  match_score: string | null;
  match_level: string | null;
  matched_skills: string | null;
  missing_skills: string | null;
  experience_match: boolean | null;
  education_match: boolean | null;
  language_match: boolean | null;
  position_match: boolean | null;
  match_reason: string | null;
  cover_letter: string | null;
  created_at: string | null;
  updated_at: string | null;
  source: string | null;
  is_applied: boolean | null;
}

const API_BASE_URL = 'http://localhost:8000'; // Adjust as needed

export const fetchJobMatches = async (): Promise<JobMatch[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/job-matches`);
    if (!response.ok) {
      throw new Error(`Error fetching job matches: ${response.statusText}`);
    }
    const data: JobMatch[] = await response.json();
    return data;
  } catch (error) {
    console.error('Failed to fetch job matches:', error);
    throw error;
  }
};

export const markJobApplied = async (matchId: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/job-matches/${encodeURIComponent(matchId)}/apply`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Error marking job applied: ${response.statusText}`);
  }
};

export const markJobNotApplied = async (matchId: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/job-matches/${encodeURIComponent(matchId)}/unapply`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Error reverting applied status: ${response.statusText}`);
  }
};
