'use client';

import { useState, FormEvent } from 'react';
import { motion } from 'framer-motion';
import { Key, Loader2, Sparkles, Database, Server, Shield, Zap, ChevronRight } from 'lucide-react';
import { useCinchDB } from '@/app/lib/cinchdb-context';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 }
};

const stagger = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

const features = [
  { icon: Database, title: 'Git-like Database', desc: 'Version control for your data' },
  { icon: Shield, title: 'Secure Access', desc: 'API key authentication' },
  { icon: Zap, title: 'Fast & Reliable', desc: 'Lightning-fast queries' },
];

export function ApiKeyForm() {
  const { connect, connecting, error } = useCinchDB();
  const [apiKey, setApiKey] = useState('');
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [showFeatures, setShowFeatures] = useState(true);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (apiKey.trim()) {
      await connect(apiKey.trim(), apiUrl.trim());
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0" style={{
        backgroundImage: 'linear-gradient(to bottom right, rgb(243 232 255), rgb(253 242 248), rgb(219 234 254))'
      }}>
        <div className="absolute inset-0 bg-grid-slate-900/[0.04] dark:bg-grid-slate-100/[0.02]" />
      </div>
      
      {/* Floating orbs */}
      <motion.div 
        className="absolute top-20 left-20 w-72 h-72 bg-purple-500/20 rounded-full blur-3xl"
        animate={{ 
          x: [0, 100, 0],
          y: [0, -100, 0],
        }}
        transition={{ 
          duration: 20,
          repeat: Infinity,
          ease: "linear"
        }}
      />
      <motion.div 
        className="absolute bottom-20 right-20 w-96 h-96 bg-pink-500/20 rounded-full blur-3xl"
        animate={{ 
          x: [0, -100, 0],
          y: [0, 100, 0],
        }}
        transition={{ 
          duration: 25,
          repeat: Infinity,
          ease: "linear"
        }}
      />

      <motion.div 
        className="relative z-10 w-full max-w-6xl px-4"
        initial="initial"
        animate="animate"
        variants={stagger}
      >
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left side - Branding and features */}
          <motion.div 
            className={`space-y-8 ${showFeatures ? 'block' : 'hidden lg:block'}`}
            variants={fadeInUp}
          >
            <div className="text-center lg:text-left">
              <motion.div 
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary mb-6"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Sparkles className="w-4 h-4" />
                <span className="text-sm font-medium">Welcome to CinchDB</span>
              </motion.div>
              
              <h1 className="text-5xl lg:text-6xl font-bold mb-4">
                <span style={{ backgroundImage: 'linear-gradient(to right, rgb(147 51 234), rgb(219 39 119))', backgroundClip: 'text', WebkitBackgroundClip: 'text', color: 'transparent' }}>Modern Database</span>
                <br />
                <span className="text-foreground">Management</span>
              </h1>
              
              <p className="text-xl text-muted-foreground">
                Experience the power of Git-like version control for your SQLite databases.
              </p>
            </div>

            <motion.div className="space-y-4" variants={stagger}>
              {features.map((feature, index) => (
                <motion.div
                  key={index}
                  className="flex items-start gap-4 p-4 rounded-xl glass glass-hover"
                  variants={fadeInUp}
                  whileHover={{ x: 10 }}
                >
                  <div className="flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center" style={{ background: 'linear-gradient(to right, rgb(147 51 234), rgb(219 39 119))' }}>
                    <feature.icon className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">{feature.title}</h3>
                    <p className="text-sm text-muted-foreground">{feature.desc}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>

          {/* Right side - Auth form */}
          <motion.div variants={fadeInUp}>
            <Card className="glass border-0 shadow-2xl">
              <CardHeader className="space-y-1 text-center pb-8">
                <motion.div 
                  className="mx-auto mb-4 w-20 h-20 rounded-2xl flex items-center justify-center shadow-glow"
                  style={{ background: 'linear-gradient(to right, rgb(147 51 234), rgb(219 39 119))' }}
                  whileHover={{ rotate: 360 }}
                  transition={{ duration: 0.5 }}
                >
                  <Key className="h-10 w-10 text-white" />
                </motion.div>
                <CardTitle className="text-3xl font-bold">Connect to CinchDB</CardTitle>
                <CardDescription className="text-base">
                  Enter your credentials to access your databases
                </CardDescription>
              </CardHeader>
              
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  <motion.div 
                    className="space-y-2"
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <Label htmlFor="api-url" className="text-sm font-medium flex items-center gap-2">
                      <Server className="w-4 h-4 text-muted-foreground" />
                      API URL
                    </Label>
                    <Input
                      id="api-url"
                      type="url"
                      value={apiUrl}
                      onChange={(e) => setApiUrl(e.target.value)}
                      placeholder="http://localhost:8000"
                      className="h-12 px-4 glass border-0 focus:ring-2 focus:ring-primary/50"
                    />
                  </motion.div>
                  
                  <motion.div 
                    className="space-y-2"
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <Label htmlFor="api-key" className="text-sm font-medium flex items-center gap-2">
                      <Key className="w-4 h-4 text-muted-foreground" />
                      API Key
                    </Label>
                    <Input
                      id="api-key"
                      type="password"
                      required
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Enter your API key"
                      className="h-12 px-4 glass border-0 focus:ring-2 focus:ring-primary/50"
                    />
                  </motion.div>

                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <Alert variant="destructive" className="glass border-red-500/20">
                        <AlertTitle>Connection failed</AlertTitle>
                        <AlertDescription>{error}</AlertDescription>
                      </Alert>
                    </motion.div>
                  )}

                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Button
                      type="submit"
                      disabled={connecting || !apiKey.trim()}
                      className="w-full h-12 text-base font-medium text-white border-0 shadow-glow-lg hover:shadow-glow transition-all duration-300"
                      style={{ background: 'linear-gradient(to right, rgb(147 51 234), rgb(219 39 119))' }}
                    >
                      {connecting ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          Connecting...
                        </>
                      ) : (
                        <>
                          Connect to Database
                          <ChevronRight className="ml-2 h-5 w-5" />
                        </>
                      )}
                    </Button>
                  </motion.div>

                  <div className="text-center">
                    <button
                      type="button"
                      onClick={() => setShowFeatures(!showFeatures)}
                      className="lg:hidden text-sm text-muted-foreground hover:text-primary transition-colors"
                    >
                      {showFeatures ? 'Hide features' : 'Show features'}
                    </button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}