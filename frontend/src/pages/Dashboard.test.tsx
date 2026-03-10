import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from './Dashboard';

// Mock useAuth for the Layout component
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'u1', name: 'Test User', role: 'user' },
    isAdmin: false,
    logout: vi.fn(),
  }),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

// Mock the api module
vi.mock('@/lib/api', () => ({
  getDueFollowUps: vi.fn(),
  getOverdueFollowUps: vi.fn(),
  getPipelineMetrics: vi.fn(),
  getExpiringCertifications: vi.fn(),
  getOpportunities: vi.fn(),
}));

import * as api from '@/lib/api';

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Dashboard />
    </MemoryRouter>
  );
}

describe('Dashboard page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading spinner initially', () => {
    // Make API calls hang
    vi.mocked(api.getDueFollowUps).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.getOverdueFollowUps).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.getPipelineMetrics).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.getExpiringCertifications).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.getOpportunities).mockReturnValue(new Promise(() => {}));

    renderDashboard();

    // The Loader2 spinner has the animate-spin class
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('renders dashboard content after data loads', async () => {
    vi.mocked(api.getDueFollowUps).mockResolvedValue([]);
    vi.mocked(api.getOverdueFollowUps).mockResolvedValue([]);
    vi.mocked(api.getPipelineMetrics).mockResolvedValue({
      total_opportunities: 12,
      pipeline_value: 5000000,
      expected_award_revenue: 2000000,
      win_rate: 0.4,
      average_deal_size: 500000,
      by_stage: {},
      by_agency: {},
    });
    vi.mocked(api.getExpiringCertifications).mockResolvedValue([]);
    vi.mocked(api.getOpportunities).mockResolvedValue([]);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    // Pipeline metrics should render
    expect(screen.getByText('Pipeline Value')).toBeInTheDocument();
    expect(screen.getByText('$5.0M')).toBeInTheDocument();
    expect(screen.getByText('12 total opportunities')).toBeInTheDocument();
    expect(screen.getByText('Expected Revenue')).toBeInTheDocument();
    expect(screen.getByText('$2.0M')).toBeInTheDocument();

    // Follow-ups card
    expect(screen.getByText('Follow-ups')).toBeInTheDocument();

    // Active Opportunities card
    expect(screen.getByText('Active Opportunities')).toBeInTheDocument();
  });

  it('renders follow-up counts correctly', async () => {
    const dueContact = {
      id: 'c1',
      first_name: 'John',
      last_name: 'Doe',
      email: 'john@example.com',
      phone: '555-1234',
      organization: 'ACME Corp',
      contact_type: 'government' as const,
      status: 'warm' as const,
      needs_follow_up: true,
      follow_up_date: '2025-06-01',
      notes: '',
      created_at: '2025-01-01T00:00:00Z',
      assigned_user_id: 'u1',
    };
    const overdueContact = {
      ...dueContact,
      id: 'c2',
      first_name: 'Jane',
      last_name: 'Smith',
      organization: 'GOV Agency',
      follow_up_date: '2025-01-01',
    };

    vi.mocked(api.getDueFollowUps).mockResolvedValue([dueContact]);
    vi.mocked(api.getOverdueFollowUps).mockResolvedValue([overdueContact]);
    vi.mocked(api.getPipelineMetrics).mockResolvedValue(null as unknown as api.PipelineMetrics);
    vi.mocked(api.getExpiringCertifications).mockResolvedValue([]);
    vi.mocked(api.getOpportunities).mockResolvedValue([]);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    // Total follow-ups = 2 (1 overdue + 1 due)
    expect(screen.getByText('2')).toBeInTheDocument();
    // Overdue section
    expect(screen.getByText('Overdue Follow-ups')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    // Due section
    expect(screen.getByText('Follow-ups Due Soon')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('shows "No action items" when there are no follow-ups or opportunities', async () => {
    vi.mocked(api.getDueFollowUps).mockResolvedValue([]);
    vi.mocked(api.getOverdueFollowUps).mockResolvedValue([]);
    vi.mocked(api.getPipelineMetrics).mockResolvedValue(null as unknown as api.PipelineMetrics);
    vi.mocked(api.getExpiringCertifications).mockResolvedValue([]);
    vi.mocked(api.getOpportunities).mockResolvedValue([]);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('No action items at the moment.')).toBeInTheDocument();
    });
  });
});
