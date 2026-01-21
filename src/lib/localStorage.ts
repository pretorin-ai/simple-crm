// LocalStorage utilities for CRM data persistence

export interface Contact {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  organization: string;
  contactType: 'individual' | 'government' | 'other';
  status: 'cold' | 'warm' | 'hot';
  needsFollowUp: boolean;
  notes: string;
  createdAt: string;
  lastContactedAt?: string;
}

export interface Communication {
  id: string;
  contactId: string;
  date: string;
  type: 'email' | 'phone' | 'meeting' | 'other';
  notes: string;
  createdAt: string;
}

export interface ContractOpportunity {
  id: string;
  title: string;
  description: string;
  source: string;
  deadline: string;
  status: 'prospective' | 'in progress' | 'submitted' | 'not a good fit';
  submissionLink?: string;
  assignedContactIds: string[];
  notes: string;
  createdAt: string;
}

export interface User {
  email: string;
  name: string;
}

const STORAGE_KEYS = {
  CONTACTS: 'crm_contacts',
  COMMUNICATIONS: 'crm_communications',
  CONTRACTS: 'crm_contracts',
  USER: 'crm_user',
} as const;

// Generic storage functions
function getFromStorage<T>(key: string, defaultValue: T): T {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.error(`Error reading ${key} from localStorage:`, error);
    return defaultValue;
  }
}

function saveToStorage<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error(`Error saving ${key} to localStorage:`, error);
  }
}

// Contacts
export function getContacts(): Contact[] {
  return getFromStorage<Contact[]>(STORAGE_KEYS.CONTACTS, []);
}

export function saveContact(contact: Contact): void {
  const contacts = getContacts();
  const index = contacts.findIndex(c => c.id === contact.id);
  if (index >= 0) {
    contacts[index] = contact;
  } else {
    contacts.push(contact);
  }
  saveToStorage(STORAGE_KEYS.CONTACTS, contacts);
}

export function deleteContact(id: string): void {
  const contacts = getContacts().filter(c => c.id !== id);
  saveToStorage(STORAGE_KEYS.CONTACTS, contacts);
}

// Communications
export function getCommunications(): Communication[] {
  return getFromStorage<Communication[]>(STORAGE_KEYS.COMMUNICATIONS, []);
}

export function saveCommunication(communication: Communication): void {
  const communications = getCommunications();
  communications.push(communication);
  saveToStorage(STORAGE_KEYS.COMMUNICATIONS, communications);
  
  // Update last contacted date on the contact
  const contacts = getContacts();
  const contact = contacts.find(c => c.id === communication.contactId);
  if (contact) {
    contact.lastContactedAt = communication.date;
    saveContact(contact);
  }
}

export function getCommunicationsForContact(contactId: string): Communication[] {
  return getCommunications().filter(c => c.contactId === contactId);
}

// Contract Opportunities
export function getContracts(): ContractOpportunity[] {
  return getFromStorage<ContractOpportunity[]>(STORAGE_KEYS.CONTRACTS, []);
}

export function saveContract(contract: ContractOpportunity): void {
  const contracts = getContracts();
  const index = contracts.findIndex(c => c.id === contract.id);
  if (index >= 0) {
    contracts[index] = contract;
  } else {
    contracts.push(contract);
  }
  saveToStorage(STORAGE_KEYS.CONTRACTS, contracts);
}

export function deleteContract(id: string): void {
  const contracts = getContracts().filter(c => c.id !== id);
  saveToStorage(STORAGE_KEYS.CONTRACTS, contracts);
}

// User/Auth
export function getUser(): User | null {
  return getFromStorage<User | null>(STORAGE_KEYS.USER, null);
}

export function saveUser(user: User): void {
  saveToStorage(STORAGE_KEYS.USER, user);
}

export function clearUser(): void {
  localStorage.removeItem(STORAGE_KEYS.USER);
}

// Generate unique ID
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}
