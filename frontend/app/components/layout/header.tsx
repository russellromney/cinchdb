'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LogOut, 
  Database, 
  GitBranch, 
  Users, 
  Sun, 
  Moon, 
  Monitor,
  Command,
  Bell,
  Settings,
  ChevronDown,
  Sparkles,
  Activity
} from 'lucide-react';
import { useCinchDB } from '@/app/lib/cinchdb-context';
import { useTheme } from '@/app/lib/theme-provider';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

const themeIcons = {
  light: Sun,
  dark: Moon,
  system: Monitor,
};

export function Header() {
  const { 
    disconnect, 
    currentDatabase, 
    currentBranch, 
    currentTenant,
    databases,
    branches,
    tenants,
    setDatabase,
    setBranch,
    setTenant,
  } = useCinchDB();
  
  const { theme, setTheme } = useTheme();
  const [isConnected, setIsConnected] = useState(true);
  
  // Simulate connection status
  useEffect(() => {
    const interval = setInterval(() => {
      setIsConnected(Math.random() > 0.1);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const ThemeIcon = themeIcons[theme];

  return (
    <TooltipProvider>
      <header className="sticky top-0 z-50 w-full border-b glass">
        <div className="flex h-16 items-center px-4 lg:px-6">
          {/* Logo and Brand */}
          <motion.div 
            className="flex items-center space-x-4"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="flex items-center space-x-3">
              <motion.div 
                className="relative"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center shadow-glow">
                  <Database className="h-6 w-6 text-white" />
                </div>
                <AnimatePresence>
                  {isConnected && (
                    <motion.div
                      className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-background"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                    >
                      <div className="pulse-dot w-full h-full bg-green-500" />
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
              <div>
                <h1 className="text-xl font-bold">
                  <span className="text-gradient gradient-primary">CinchDB</span>
                </h1>
                <p className="text-xs text-muted-foreground">
                  {isConnected ? 'Connected' : 'Connecting...'}
                </p>
              </div>
            </div>
            
            <Separator orientation="vertical" className="h-8 mx-2" />
          </motion.div>
          
          {/* Database Selectors */}
          <div className="flex items-center space-x-3 flex-1">
            <motion.div 
              className="flex items-center space-x-2"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Database className="h-4 w-4 text-muted-foreground" />
              <Select value={currentDatabase} onValueChange={setDatabase}>
                <SelectTrigger className="w-[180px] h-9 glass border-0 hover:shadow-md transition-all">
                  <SelectValue placeholder="Select database" />
                </SelectTrigger>
                <SelectContent className="glass">
                  {databases.map((db) => (
                    <SelectItem key={db.name} value={db.name}>
                      <div className="flex items-center gap-2">
                        <Activity className="h-3 w-3 text-muted-foreground" />
                        {db.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </motion.div>

            <motion.div 
              className="flex items-center space-x-2"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <GitBranch className="h-4 w-4 text-muted-foreground" />
              <Select value={currentBranch} onValueChange={setBranch}>
                <SelectTrigger className="w-[180px] h-9 glass border-0 hover:shadow-md transition-all">
                  <SelectValue placeholder="Select branch" />
                </SelectTrigger>
                <SelectContent className="glass">
                  {branches.map((branch) => (
                    <SelectItem key={branch.name} value={branch.name}>
                      <div className="flex items-center gap-2">
                        {branch.name}
                        {branch.name === 'main' && (
                          <Badge variant="secondary" className="h-4 text-xs px-1">
                            default
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </motion.div>

            <motion.div 
              className="flex items-center space-x-2"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Users className="h-4 w-4 text-muted-foreground" />
              <Select value={currentTenant} onValueChange={setTenant}>
                <SelectTrigger className="w-[180px] h-9 glass border-0 hover:shadow-md transition-all">
                  <SelectValue placeholder="Select tenant" />
                </SelectTrigger>
                <SelectContent className="glass">
                  {tenants.map((tenant) => (
                    <SelectItem key={tenant.name} value={tenant.name}>
                      <div className="flex items-center gap-2">
                        {tenant.name}
                        {tenant.name === 'main' && (
                          <Badge variant="secondary" className="h-4 text-xs px-1">
                            default
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </motion.div>
          </div>

          {/* Right side actions */}
          <motion.div 
            className="flex items-center space-x-2"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            {/* Command palette hint */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="hidden lg:flex glass-hover"
                  onClick={() => {
                    // Command palette will be implemented later
                    const event = new KeyboardEvent('keydown', {
                      key: 'k',
                      metaKey: true,
                      ctrlKey: true,
                    });
                    window.dispatchEvent(event);
                  }}
                >
                  <Command className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="glass">
                <p className="flex items-center gap-2">
                  Quick Actions
                  <kbd className="px-2 py-0.5 text-xs font-mono bg-muted rounded">⌘K</kbd>
                </p>
              </TooltipContent>
            </Tooltip>

            {/* Notifications */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="relative glass-hover">
                  <Bell className="h-4 w-4" />
                  <span className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="glass">
                <p>Notifications</p>
              </TooltipContent>
            </Tooltip>

            {/* Theme switcher */}
            <DropdownMenu>
              <Tooltip>
                <TooltipTrigger asChild>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="glass-hover">
                      <ThemeIcon className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="glass">
                  <p>Change theme</p>
                </TooltipContent>
              </Tooltip>
              <DropdownMenuContent align="end" className="glass">
                <DropdownMenuLabel>Theme</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setTheme('light')}>
                  <Sun className="mr-2 h-4 w-4" />
                  Light
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme('dark')}>
                  <Moon className="mr-2 h-4 w-4" />
                  Dark
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme('system')}>
                  <Monitor className="mr-2 h-4 w-4" />
                  System
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <Separator orientation="vertical" className="h-8 mx-2" />

            {/* User menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button 
                  variant="ghost" 
                  className="relative h-9 px-3 glass-hover"
                >
                  <Avatar className="h-7 w-7 mr-2">
                    <AvatarFallback className="gradient-primary text-white text-xs">
                      U
                    </AvatarFallback>
                  </Avatar>
                  <span className="hidden lg:inline-block">User</span>
                  <ChevronDown className="ml-2 h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 glass">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">User</p>
                    <p className="text-xs leading-none text-muted-foreground">
                      user@example.com
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Upgrade to Pro
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  onClick={disconnect}
                  className="text-destructive focus:text-destructive"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Disconnect
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </motion.div>
        </div>
      </header>
    </TooltipProvider>
  );
}