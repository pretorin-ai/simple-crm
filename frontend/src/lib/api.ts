// API client for backend communication

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const REQUEST_TIMEOUT_MS = 30000;

export interface ApiError {
  detail: string;
}

// Auth token management
export function getAuthToken(): string | null {
  return localStorage.getItem('auth_token');
}

export function setAuthToken(token: string): void {
  localStorage.setItem('auth_token', token);
}

export function clearAuthToken(): void {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('refresh_token');
}

export function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token');
}

export function setRefreshToken(token: string): void {
  localStorage.setItem('refresh_token', token);
}

// Attempt to refresh the access token using the stored refresh token.
// Returns true if the token was successfully refreshed.
let _refreshPromise: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
      signal: controller.signal,
    });
    if (!response.ok) return false;
    const data = await response.json();
    setAuthToken(data.access_token);
    if (data.refresh_token) setRefreshToken(data.refresh_token);
    return true;
  } catch {
    return false;
  } finally {
    clearTimeout(timeoutId);
  }
}

// Generic fetch wrapper with auth
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
    });

    if (!response.ok) {
      if (response.status === 401) {
        // For non-auth endpoints, try refreshing the token first
        if (!endpoint.startsWith('/auth/')) {
          if (!_refreshPromise) {
            _refreshPromise = tryRefreshToken().finally(() => { _refreshPromise = null; });
          }
          const refreshed = await _refreshPromise;
          if (refreshed) {
            clearTimeout(timeoutId);
            return fetchApi<T>(endpoint, options);
          }
        }
        clearAuthToken();
        window.dispatchEvent(new Event('auth:unauthorized'));
      }
      let errorMessage = `Request failed (${response.status})`;
      try {
        const text = await response.text();
        try {
          const error = JSON.parse(text);
          if (typeof error.detail === 'string') {
            errorMessage = error.detail;
          } else if (Array.isArray(error.detail)) {
            errorMessage = error.detail.map((e: { msg: string }) => e.msg).join(', ');
          }
        } catch {
          if (text) errorMessage = text;
        }
      } catch {
        // Can't read response body
      }
      throw new Error(errorMessage);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as unknown as T;
    }

    return response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

// Auth API
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthToken {
  access_token: string;
  refresh_token?: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  is_active: boolean;
  auth_provider?: string;
  created_at: string;
  updated_at: string;
}

export interface UserCreateByAdmin {
  email: string;
  name: string;
  password: string;
  role: 'admin' | 'user';
}

export interface UserUpdate {
  name?: string;
  email?: string;
  role?: 'admin' | 'user';
  is_active?: boolean;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordReset {
  token: string;
  new_password: string;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

export async function login(credentials: LoginCredentials): Promise<AuthToken> {
  return fetchApi<AuthToken>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

export async function googleLogin(credential: string): Promise<AuthToken> {
  return fetchApi<AuthToken>('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ credential }),
  });
}

export async function getCurrentUser(): Promise<User> {
  return fetchApi<User>('/auth/me');
}

// Contacts API
export interface Contact {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  organization: string;
  contact_type: 'individual' | 'commercial' | 'government';
  status: 'cold' | 'warm' | 'hot';
  needs_follow_up: boolean;
  follow_up_date?: string;
  notes: string;
  created_at: string;
  last_contacted_at?: string;
  assigned_user_id: string;
  assigned_user?: User;
}

export interface ContactCreate {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  organization: string;
  contact_type: 'individual' | 'commercial' | 'government';
  status: 'cold' | 'warm' | 'hot';
  needs_follow_up: boolean;
  follow_up_date?: string;
  notes: string;
  assigned_user_id?: string;
}

export async function getContacts(): Promise<Contact[]> {
  return fetchApi<Contact[]>('/contacts');
}

export async function getContact(id: string): Promise<Contact> {
  return fetchApi<Contact>(`/contacts/${id}`);
}

export async function createContact(contact: ContactCreate): Promise<Contact> {
  return fetchApi<Contact>('/contacts', {
    method: 'POST',
    body: JSON.stringify(contact),
  });
}

export async function updateContact(id: string, contact: ContactCreate): Promise<Contact> {
  return fetchApi<Contact>(`/contacts/${id}`, {
    method: 'PUT',
    body: JSON.stringify(contact),
  });
}

export async function patchContact(id: string, updates: Partial<ContactCreate>): Promise<Contact> {
  return fetchApi<Contact>(`/contacts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export async function deleteContact(id: string): Promise<void> {
  return fetchApi<void>(`/contacts/${id}`, {
    method: 'DELETE',
  });
}

// Communications API
export interface Communication {
  id: string;
  contact_id: string;
  date: string;
  type: 'email' | 'phone' | 'meeting' | 'other';
  notes: string;
  created_at: string;
  subject?: string;
  email_from?: string;
  email_to?: string;
  body_html?: string;
  gmail_message_id?: string;
  gmail_thread_id?: string;
  direction?: 'inbound' | 'outbound';
}

export interface CommunicationCreate {
  contact_id: string;
  date: string;
  type: 'email' | 'phone' | 'meeting' | 'other';
  notes: string;
}

export async function getCommunications(contactId?: string): Promise<Communication[]> {
  const params = new URLSearchParams();
  if (contactId) {
    params.set('contact_id', contactId);
  }
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchApi<Communication[]>(`/communications${query}`);
}

export async function createCommunication(communication: CommunicationCreate): Promise<Communication> {
  return fetchApi<Communication>('/communications', {
    method: 'POST',
    body: JSON.stringify(communication),
  });
}

export async function deleteCommunication(id: string): Promise<void> {
  return fetchApi<void>(`/communications/${id}`, {
    method: 'DELETE',
  });
}

// Contracts API
export interface ContactBrief {
  id: string;
  first_name: string;
  last_name: string;
}

export interface Contract {
  id: string;
  title: string;
  description: string;
  source: string;
  deadline: string;
  status: 'prospective' | 'in progress' | 'submitted' | 'not a good fit';
  submission_link?: string;
  notes: string;
  created_at: string;
  assigned_contact_ids: string[];
  assigned_contacts: ContactBrief[];
}

export interface ContractCreate {
  title: string;
  description: string;
  source: string;
  deadline: string;
  status: 'prospective' | 'in progress' | 'submitted' | 'not a good fit';
  submission_link?: string;
  notes: string;
  assigned_contact_ids: string[];
}

export async function getContracts(): Promise<Contract[]> {
  return fetchApi<Contract[]>('/contracts');
}

export async function getContract(id: string): Promise<Contract> {
  return fetchApi<Contract>(`/contracts/${id}`);
}

export async function createContract(contract: ContractCreate): Promise<Contract> {
  return fetchApi<Contract>('/contracts', {
    method: 'POST',
    body: JSON.stringify(contract),
  });
}

export async function updateContract(id: string, contract: ContractCreate): Promise<Contract> {
  return fetchApi<Contract>(`/contracts/${id}`, {
    method: 'PUT',
    body: JSON.stringify(contract),
  });
}

export async function patchContract(id: string, updates: Partial<ContractCreate>): Promise<Contract> {
  return fetchApi<Contract>(`/contracts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export async function deleteContract(id: string): Promise<void> {
  return fetchApi<void>(`/contracts/${id}`, {
    method: 'DELETE',
  });
}

// Follow-up specific endpoints
export async function getDueFollowUps(daysAhead: number = 7): Promise<Contact[]> {
  const params = new URLSearchParams({ days_ahead: String(daysAhead) });
  return fetchApi<Contact[]>(`/contacts/follow-ups/due?${params.toString()}`);
}

export async function getOverdueFollowUps(): Promise<Contact[]> {
  return fetchApi<Contact[]>('/contacts/follow-ups/overdue');
}

// Users API
export async function getUsers(): Promise<User[]> {
  return fetchApi<User[]>('/users');
}

export async function getUser(userId: string): Promise<User> {
  return fetchApi<User>(`/users/${userId}`);
}

export async function createUser(user: UserCreateByAdmin): Promise<User> {
  return fetchApi<User>('/users', {
    method: 'POST',
    body: JSON.stringify(user),
  });
}

export async function updateUser(userId: string, updates: UserUpdate): Promise<User> {
  return fetchApi<User>(`/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

export async function deleteUser(userId: string): Promise<{ message: string }> {
  return fetchApi<{ message: string }>(`/users/${userId}`, {
    method: 'DELETE',
  });
}

// Password reset API
export async function requestPasswordReset(email: string): Promise<{ message: string }> {
  return fetchApi<{ message: string }>('/auth/password-reset-request', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(data: PasswordReset): Promise<{ message: string }> {
  return fetchApi<{ message: string }>('/auth/password-reset', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function changePassword(data: PasswordChange): Promise<{ message: string }> {
  return fetchApi<{ message: string }>('/auth/password-change', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// API Key Management
export interface ApiKeyResponse {
  api_key: string;
  message: string;
}

export interface ApiKeyStatus {
  has_api_key: boolean;
  api_key_prefix: string | null;
}

export async function generateApiKey(): Promise<ApiKeyResponse> {
  return fetchApi<ApiKeyResponse>('/users/me/api-key/generate', {
    method: 'POST',
  });
}

export async function revokeApiKey(): Promise<{ message: string }> {
  return fetchApi<{ message: string }>('/users/me/api-key', {
    method: 'DELETE',
  });
}

export async function getApiKeyStatus(): Promise<ApiKeyStatus> {
  return fetchApi<ApiKeyStatus>('/users/me/api-key/status');
}

// Accounts API
export interface Account {
  id: string;
  name: string;
  account_type: 'government_agency' | 'prime_contractor' | 'subcontractor' | 'partner' | 'vendor';
  parent_agency?: string;
  office?: string;
  location?: string;
  website?: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface AccountCreate {
  name: string;
  account_type: Account['account_type'];
  parent_agency?: string;
  office?: string;
  location?: string;
  website?: string;
  notes: string;
}

export async function getAccounts(accountType?: string): Promise<Account[]> {
  const params = new URLSearchParams();
  if (accountType) params.set('account_type', accountType);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchApi<Account[]>(`/accounts${query}`);
}

export async function getAccount(id: string): Promise<Account> {
  return fetchApi<Account>(`/accounts/${id}`);
}

export async function createAccount(account: AccountCreate): Promise<Account> {
  return fetchApi<Account>('/accounts', { method: 'POST', body: JSON.stringify(account) });
}

export async function updateAccount(id: string, account: AccountCreate): Promise<Account> {
  return fetchApi<Account>(`/accounts/${id}`, { method: 'PUT', body: JSON.stringify(account) });
}

export async function deleteAccount(id: string): Promise<void> {
  return fetchApi<void>(`/accounts/${id}`, { method: 'DELETE' });
}

// Opportunities API
export interface VehicleBrief {
  id: string;
  name: string;
}

export interface Opportunity {
  id: string;
  title: string;
  is_government_contract: boolean;
  description: string;
  agency?: string;
  account_id?: string;
  naics_code?: string;
  set_aside_type?: 'small_business' | '8a' | 'hubzone' | 'wosb' | 'sdvosb' | 'full_and_open' | 'none';
  estimated_value?: number;
  solicitation_number?: string;
  sam_gov_notice_id?: string;
  submission_link?: string;
  deadline?: string;
  source?: 'sam_gov' | 'agency_forecast' | 'incumbent_recompete' | 'partner_referral' | 'internal';
  stage: 'identified' | 'qualified' | 'capture' | 'teaming' | 'proposal' | 'submitted' | 'awarded' | 'lost';
  capture_manager_id?: string;
  expected_release_date?: string;
  proposal_due_date?: string;
  award_date_estimate?: string;
  win_probability?: number;
  notes: string;
  created_at: string;
  updated_at: string;
  created_by_user_id?: string;
  vehicle_ids: string[];
  vehicles: VehicleBrief[];
}

export interface OpportunityCreate {
  title: string;
  is_government_contract: boolean;
  description: string;
  agency?: string;
  account_id?: string;
  naics_code?: string;
  set_aside_type?: Opportunity['set_aside_type'];
  estimated_value?: number;
  solicitation_number?: string;
  sam_gov_notice_id?: string;
  submission_link?: string;
  deadline?: string;
  source?: Opportunity['source'];
  stage: Opportunity['stage'];
  capture_manager_id?: string;
  expected_release_date?: string;
  proposal_due_date?: string;
  award_date_estimate?: string;
  win_probability?: number;
  notes: string;
  vehicle_ids: string[];
}

export interface PipelineMetrics {
  total_opportunities: number;
  pipeline_value: number;
  expected_award_revenue: number;
  win_rate: number;
  average_deal_size: number;
  by_stage: Record<string, { count: number; value: number }>;
  by_agency: Record<string, { count: number; value: number }>;
}

export async function getOpportunities(filters?: {
  stage?: string;
  agency?: string;
  naics_code?: string;
  set_aside_type?: string;
  source?: string;
  search?: string;
  min_value?: number;
  max_value?: number;
}): Promise<Opportunity[]> {
  const params = new URLSearchParams();
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') params.set(key, String(value));
    });
  }
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchApi<Opportunity[]>(`/opportunities${query}`);
}

export async function getOpportunity(id: string): Promise<Opportunity> {
  return fetchApi<Opportunity>(`/opportunities/${id}`);
}

export async function getPipelineMetrics(): Promise<PipelineMetrics> {
  return fetchApi<PipelineMetrics>('/opportunities/pipeline');
}

export async function createOpportunity(opp: OpportunityCreate): Promise<Opportunity> {
  return fetchApi<Opportunity>('/opportunities', { method: 'POST', body: JSON.stringify(opp) });
}

export async function updateOpportunity(id: string, opp: OpportunityCreate): Promise<Opportunity> {
  return fetchApi<Opportunity>(`/opportunities/${id}`, { method: 'PUT', body: JSON.stringify(opp) });
}

export async function patchOpportunity(id: string, updates: Partial<OpportunityCreate>): Promise<Opportunity> {
  return fetchApi<Opportunity>(`/opportunities/${id}`, { method: 'PATCH', body: JSON.stringify(updates) });
}

export async function deleteOpportunity(id: string): Promise<void> {
  return fetchApi<void>(`/opportunities/${id}`, { method: 'DELETE' });
}

// Opportunity Timeline API
export interface OpportunityEvent {
  id: string;
  opportunity_id: string;
  date: string;
  event_type: 'discovery' | 'contact' | 'rfp_release' | 'proposal_submitted' | 'meeting' | 'stage_change' | 'note' | 'other';
  description: string;
  created_by_user_id?: string;
  created_at: string;
}

export interface OpportunityEventCreate {
  opportunity_id: string;
  date: string;
  event_type: OpportunityEvent['event_type'];
  description: string;
}

export async function getTimeline(opportunityId: string): Promise<OpportunityEvent[]> {
  return fetchApi<OpportunityEvent[]>(`/opportunities/${opportunityId}/timeline`);
}

export async function createTimelineEvent(opportunityId: string, event: OpportunityEventCreate): Promise<OpportunityEvent> {
  return fetchApi<OpportunityEvent>(`/opportunities/${opportunityId}/timeline`, { method: 'POST', body: JSON.stringify(event) });
}

export async function deleteTimelineEvent(opportunityId: string, eventId: string): Promise<void> {
  return fetchApi<void>(`/opportunities/${opportunityId}/timeline/${eventId}`, { method: 'DELETE' });
}

// Capture Notes API
export interface CaptureNote {
  id: string;
  opportunity_id: string;
  section: 'customer_intel' | 'incumbent' | 'competitors' | 'partners' | 'risks' | 'strategy';
  content: string;
  updated_at: string;
}

export async function getCaptureNotes(opportunityId: string): Promise<CaptureNote[]> {
  return fetchApi<CaptureNote[]>(`/opportunities/${opportunityId}/capture-notes`);
}

export async function upsertCaptureNote(opportunityId: string, section: string, content: string): Promise<CaptureNote> {
  return fetchApi<CaptureNote>(`/opportunities/${opportunityId}/capture-notes/${section}`, { method: 'PUT', body: JSON.stringify({ content }) });
}

// Attachments API
export interface AttachmentRecord {
  id: string;
  opportunity_id: string;
  filename: string;
  content_type?: string;
  size?: number;
  uploaded_by_user_id?: string;
  created_at: string;
}

export async function getAttachments(opportunityId: string): Promise<AttachmentRecord[]> {
  return fetchApi<AttachmentRecord[]>(`/opportunities/${opportunityId}/attachments`);
}

export async function uploadAttachment(opportunityId: string, file: File): Promise<AttachmentRecord> {
  const formData = new FormData();
  formData.append('file', file);
  const token = getAuthToken();
  const res = await fetch(`${API_BASE_URL}/opportunities/${opportunityId}/attachments`, {
    method: 'POST',
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function deleteAttachment(opportunityId: string, attachmentId: string): Promise<void> {
  return fetchApi<void>(`/opportunities/${opportunityId}/attachments/${attachmentId}`, { method: 'DELETE' });
}

export function getAttachmentDownloadUrl(opportunityId: string, attachmentId: string): string {
  return `${API_BASE_URL}/opportunities/${opportunityId}/attachments/${attachmentId}/download`;
}

// Contract Vehicles API
export interface ContractVehicle {
  id: string;
  name: string;
  agency?: string;
  contract_number?: string;
  expiration_date?: string;
  ceiling_value?: number;
  prime_or_sub?: 'prime' | 'sub';
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ContractVehicleCreate {
  name: string;
  agency?: string;
  contract_number?: string;
  expiration_date?: string;
  ceiling_value?: number;
  prime_or_sub?: 'prime' | 'sub';
  notes: string;
}

export async function getVehicles(): Promise<ContractVehicle[]> {
  return fetchApi<ContractVehicle[]>('/vehicles');
}

export async function getVehicle(id: string): Promise<ContractVehicle> {
  return fetchApi<ContractVehicle>(`/vehicles/${id}`);
}

export async function createVehicle(vehicle: ContractVehicleCreate): Promise<ContractVehicle> {
  return fetchApi<ContractVehicle>('/vehicles', { method: 'POST', body: JSON.stringify(vehicle) });
}

export async function updateVehicle(id: string, vehicle: ContractVehicleCreate): Promise<ContractVehicle> {
  return fetchApi<ContractVehicle>(`/vehicles/${id}`, { method: 'PUT', body: JSON.stringify(vehicle) });
}

export async function deleteVehicle(id: string): Promise<void> {
  return fetchApi<void>(`/vehicles/${id}`, { method: 'DELETE' });
}

// Teaming API
export interface AccountBrief {
  id: string;
  name: string;
  account_type: string;
}

export interface TeamingRecord {
  id: string;
  opportunity_id: string;
  partner_account_id: string;
  role: 'prime' | 'subcontractor' | 'jv_partner';
  status: 'potential' | 'nda_signed' | 'teaming_agreed' | 'active' | 'inactive';
  notes: string;
  created_at: string;
  updated_at: string;
  partner_account?: AccountBrief;
}

export interface TeamingCreate {
  opportunity_id: string;
  partner_account_id: string;
  role: TeamingRecord['role'];
  status: TeamingRecord['status'];
  notes: string;
}

export async function getTeamingRecords(opportunityId?: string): Promise<TeamingRecord[]> {
  const params = new URLSearchParams();
  if (opportunityId) params.set('opportunity_id', opportunityId);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchApi<TeamingRecord[]>(`/teaming${query}`);
}

export async function createTeaming(teaming: TeamingCreate): Promise<TeamingRecord> {
  return fetchApi<TeamingRecord>('/teaming', { method: 'POST', body: JSON.stringify(teaming) });
}

export async function deleteTeaming(id: string): Promise<void> {
  return fetchApi<void>(`/teaming/${id}`, { method: 'DELETE' });
}

// Proposals API
export interface Proposal {
  id: string;
  opportunity_id: string;
  proposal_manager_id?: string;
  submission_type?: 'full' | 'partial' | 'draft';
  submission_deadline?: string;
  status: 'not_started' | 'in_progress' | 'review' | 'final' | 'submitted';
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ProposalCreate {
  opportunity_id: string;
  proposal_manager_id?: string;
  submission_type?: Proposal['submission_type'];
  submission_deadline?: string;
  status: Proposal['status'];
  notes: string;
}

export async function getProposals(opportunityId?: string): Promise<Proposal[]> {
  const params = new URLSearchParams();
  if (opportunityId) params.set('opportunity_id', opportunityId);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchApi<Proposal[]>(`/proposals${query}`);
}

export async function createProposal(proposal: ProposalCreate): Promise<Proposal> {
  return fetchApi<Proposal>('/proposals', { method: 'POST', body: JSON.stringify(proposal) });
}

export async function patchProposal(id: string, updates: Partial<ProposalCreate>): Promise<Proposal> {
  return fetchApi<Proposal>(`/proposals/${id}`, { method: 'PATCH', body: JSON.stringify(updates) });
}

export async function deleteProposal(id: string): Promise<void> {
  return fetchApi<void>(`/proposals/${id}`, { method: 'DELETE' });
}

// Compliance API
export interface ComplianceRecord {
  id: string;
  certification_type: 'small_business' | '8a' | 'hubzone' | 'wosb' | 'sdvosb' | 'edwosb';
  issued_by?: string;
  issue_date?: string;
  expiration_date?: string;
  status: 'active' | 'expiring_soon' | 'expired' | 'pending';
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ComplianceCreate {
  certification_type: ComplianceRecord['certification_type'];
  issued_by?: string;
  issue_date?: string;
  expiration_date?: string;
  status: ComplianceRecord['status'];
  notes: string;
}

export async function getComplianceRecords(): Promise<ComplianceRecord[]> {
  return fetchApi<ComplianceRecord[]>('/compliance');
}

export async function getExpiringCertifications(daysAhead: number = 90): Promise<ComplianceRecord[]> {
  return fetchApi<ComplianceRecord[]>(`/compliance/expiring?days_ahead=${daysAhead}`);
}

export async function createCompliance(record: ComplianceCreate): Promise<ComplianceRecord> {
  return fetchApi<ComplianceRecord>('/compliance', { method: 'POST', body: JSON.stringify(record) });
}

export async function updateCompliance(id: string, record: ComplianceCreate): Promise<ComplianceRecord> {
  return fetchApi<ComplianceRecord>(`/compliance/${id}`, { method: 'PUT', body: JSON.stringify(record) });
}

export async function deleteCompliance(id: string): Promise<void> {
  return fetchApi<void>(`/compliance/${id}`, { method: 'DELETE' });
}

// Gmail Integration API
export interface GmailStatus {
  connected: boolean;
  gmail_address?: string;
  last_sync_at?: string;
}

export interface GmailAuthUrl {
  auth_url: string;
}

export interface GmailSendRequest {
  to: string;
  subject: string;
  body: string;
  contact_id: string;
  reply_to_message_id?: string;
  thread_id?: string;
}

export async function getGmailStatus(): Promise<GmailStatus> {
  return fetchApi<GmailStatus>('/gmail/status');
}

export async function getGmailAuthUrl(): Promise<GmailAuthUrl> {
  return fetchApi<GmailAuthUrl>('/gmail/auth-url');
}

export async function disconnectGmail(): Promise<void> {
  return fetchApi<void>('/gmail/disconnect', { method: 'DELETE' });
}

export async function sendGmailEmail(request: GmailSendRequest): Promise<Communication> {
  return fetchApi<Communication>('/gmail/send', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// Gmail Contacts Import API
export interface GoogleContactPreview {
  google_resource_name: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  organization: string;
  title: string;
  already_exists: boolean;
}

export interface GoogleContactsPreviewResponse {
  contacts: GoogleContactPreview[];
  total_fetched: number;
}

export interface GoogleContactImportItem {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  organization: string;
  title: string;
  contact_type: 'individual' | 'commercial' | 'government';
  status: 'cold' | 'warm' | 'hot';
}

export interface GoogleContactImportResponse {
  imported: number;
  skipped: number;
  errors: string[];
}

export async function getGmailContactsPreview(): Promise<GoogleContactsPreviewResponse> {
  return fetchApi<GoogleContactsPreviewResponse>('/gmail/contacts/preview');
}

export async function importGmailContacts(contacts: GoogleContactImportItem[]): Promise<GoogleContactImportResponse> {
  return fetchApi<GoogleContactImportResponse>('/gmail/contacts/import', {
    method: 'POST',
    body: JSON.stringify({ contacts }),
  });
}
