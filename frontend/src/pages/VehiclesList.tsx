import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import * as api from '@/lib/api';
import { formatCurrency } from '@/lib/badges';
import { Plus, Search, Loader2, FileStack } from 'lucide-react';
import { toast } from 'sonner';

export default function VehiclesList() {
  const [searchQuery, setSearchQuery] = useState('');
  const [vehicles, setVehicles] = useState<api.ContractVehicle[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const data = await api.getVehicles();
      setVehicles(data);
    } catch (error) {
      toast.error('Failed to load vehicles');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const filtered = vehicles
    .filter((v) => {
      const query = searchQuery.toLowerCase();
      return (
        v.name.toLowerCase().includes(query) ||
        (v.agency || '').toLowerCase().includes(query) ||
        (v.contract_number || '').toLowerCase().includes(query)
      );
    })
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Contract Vehicles</h2>
            <p className="text-muted-foreground">Manage contract vehicles & schedules</p>
          </div>
          <Button asChild>
            <Link to="/vehicles/new">
              <Plus className="mr-2 h-4 w-4" />
              Add Vehicle
            </Link>
          </Button>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search vehicles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length > 0 ? (
          <div className="space-y-4">
            {filtered.map((vehicle) => (
              <Link key={vehicle.id} to={`/vehicles/${vehicle.id}`}>
                <Card className="p-6 transition-shadow hover:shadow-md">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex items-start gap-3">
                      <FileStack className="h-5 w-5 mt-0.5 text-muted-foreground shrink-0" />
                      <div>
                        <h3 className="font-semibold">{vehicle.name}</h3>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-sm text-muted-foreground">
                          {vehicle.agency && <span>{vehicle.agency}</span>}
                          {vehicle.contract_number && <span>#{vehicle.contract_number}</span>}
                          {vehicle.ceiling_value && <span>Ceiling: {formatCurrency(vehicle.ceiling_value)}</span>}
                          {vehicle.expiration_date && (
                            <span>Expires: {new Date(vehicle.expiration_date).toLocaleDateString()}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    {vehicle.prime_or_sub && (
                      <Badge variant={vehicle.prime_or_sub === 'prime' ? 'default' : 'outline'} className="self-start">
                        {vehicle.prime_or_sub}
                      </Badge>
                    )}
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        ) : (
          <Card className="p-12 text-center">
            <p className="text-muted-foreground">
              {searchQuery ? 'No vehicles found.' : 'No contract vehicles yet.'}
            </p>
          </Card>
        )}
      </div>
    </Layout>
  );
}
