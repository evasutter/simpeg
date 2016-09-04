import unittest
from SimPEG import EM, Mesh, Utils, np, Maps, sp
try:
    # from pymatsolver import PardisoSolver as Solver
    from pymatsolver import MumpsSolver as Solver
except ImportError:
    from SimPEG import SolverLU as Solver
# import sys
from scipy.constants import mu_0

# Global Test Parameters
plotIt = False
tol_NumErrZero = 1e-16

SIGMABACK = 7e-2
KAPPA = 1

# Util functions
if plotIt:
    import matplotlib.pyplot as plt

    def plotLine_num_ana(ax, x, num, ana, title=None, xlabel='x (m)'):
        ax.plot(x, num, 'o', x, ana, linewidth=2)
        ax.grid(which='both')
        if title is not None:
            ax.set_title(title)
        if xlabel is not None:
            ax.set_xlabel('x (m)')
        return ax

    def plotFields_num_ana(field, x, ana_x, ana_y, ana_z, num_x, num_y, num_z):
        fig, ax = plt.subplots(2, 3, figsize=(20, 10))
        ax = Utils.mkvc(ax)

        plotLine_num_ana(ax[0], x, num_x.real, ana_x.real, title=field+'_x Re')
        plotLine_num_ana(ax[1], x, num_x.imag, ana_x.imag, title=field+'_x Im')

        plotLine_num_ana(ax[2], x, num_y.real, ana_y.real, title=field+'_y Re')
        plotLine_num_ana(ax[3], x, num_y.imag, ana_y.imag, title=field+'_y Im')

        plotLine_num_ana(ax[4], x, num_z.real, ana_z.real, title=field+'_z Re')
        plotLine_num_ana(ax[5], x, num_z.imag, ana_z.imag, title=field+'_z Im')

        plt.legend(['Num', 'Ana'], bbox_to_anchor=(1.5, 0.5))
        plt.tight_layout()
        plt.show()


def setUpMesh(cs=5, nc=18, npad=8):
    h = Utils.meshTensor([(cs, npad, -1.3), (cs, nc), (cs, npad, 1.3)])
    return Mesh.TensorMesh([h, h, h], 'CCC')


def errorLog(field, ana_x, ana_y, ana_z, num_x, num_y, num_z, tol):

    print('{:^4} {:^25} {:^25} {:^25} {:^25} {:^11}'.format(
        'Comp', 'Ana', 'Num', 'Num-Ana', '(Num-Ana)/Ana', 'Pass Status'))

    def errLog(fieldcomp, ana, num):
        norm_ana = np.linalg.norm(ana)
        norm_num = np.linalg.norm(num)
        norm_diff = np.linalg.norm(num-ana)

        if norm_ana > tol_NumErrZero:
            check = norm_diff/norm_ana
            passed = check < tol
        else:
            check = norm_ana
            passed = check < tol_NumErrZero

        print('{:^4} {:25.10e} {:25.10e} {:25.10e} {:>25} {:^11}'.format(
            fieldcomp,
            norm_ana,
            norm_num,
            norm_diff,
            check if norm_ana > tol_NumErrZero else '-----',
            str(passed)
            ))

        return passed

    passed_x = errLog(field+'_x', ana_x, num_x)
    passed_y = errLog(field+'_y', ana_y, num_y)
    passed_z = errLog(field+'_z', ana_z, num_z)

    return passed_x, passed_y, passed_z


class X_ElecDipoleTest_3DMesh(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        print('Testing a X-oriented analytic harmonic electric dipole against '
              'the numerical solution on a 3D-tesnsor mesh.')

        # Define model parameters
        self.sigmaback = SIGMABACK
        # mu = mu_0*(1+kappa)
        self.kappa = KAPPA

        # Create 3D mesh
        self.mesh = setUpMesh()

        # Set source parameters
        self.freq = 500.
        src_loc = np.r_[0., 0., -35]
        src_loc_CCInd = Utils.closestPoints(self.mesh, src_loc, 'CC')
        self.src_loc_CC = self.mesh.gridCC[src_loc_CCInd, :]
        self.src_loc_CC = self.src_loc_CC[0]

        # Compute skin depth
        skdpth = 500. / np.sqrt(self.sigmaback * self.freq)

        # make sure mesh is big enough
        # print('skin depth =', skdpth)
        # self.assertTrue(self.mesh.hx.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hy.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hz.sum() > skdpth*2.)

        # Create wholespace models
        SigmaBack = self.sigmaback*np.ones((self.mesh.nC))
        MuBack = (mu_0*(1 + self.kappa))*np.ones((self.mesh.nC))

        # Define reciever locations
        xlim = 40.  # x locations from -50 to 50
        xInd = np.where(np.abs(self.mesh.vectorCCx) < xlim)
        x = self.mesh.vectorCCx[xInd[0]]
        y = 10.
        z = 30.

        # where we choose to measure
        XYZ = Utils.ndgrid(x, np.r_[y], np.r_[z])

        # Cell centred recievers
        XYZ_CCInd = Utils.closestPoints(self.mesh, XYZ, 'CC')
        self.XYZ_CC = self.mesh.gridCC[XYZ_CCInd, :]

        # Edge recievers
        XYZ_ExInd = Utils.closestPoints(self.mesh, XYZ, 'Ex')
        self.XYZ_Ex = self.mesh.gridEx[XYZ_ExInd, :]
        XYZ_EyInd = Utils.closestPoints(self.mesh, XYZ, 'Ey')
        self.XYZ_Ey = self.mesh.gridEy[XYZ_EyInd, :]
        XYZ_EzInd = Utils.closestPoints(self.mesh, XYZ, 'Ez')
        self.XYZ_Ez = self.mesh.gridEz[XYZ_EzInd, :]

        # Face recievers
        XYZ_FxInd = Utils.closestPoints(self.mesh, XYZ, 'Fx')
        self.XYZ_Fx = self.mesh.gridFx[XYZ_FxInd, :]
        XYZ_FyInd = Utils.closestPoints(self.mesh, XYZ, 'Fy')
        self.XYZ_Fy = self.mesh.gridFy[XYZ_FyInd, :]
        XYZ_FzInd = Utils.closestPoints(self.mesh, XYZ, 'Fz')
        self.XYZ_Fz = self.mesh.gridFz[XYZ_FzInd, :]

        # Form data interpolation matrices
        Pcc = self.mesh.getInterpolationMat(self.XYZ_CC, 'CC')
        Zero = sp.csr_matrix(Pcc.shape)
        self.Pccx, self.Pccy, self.Pccz = sp.hstack([Pcc, Zero, Zero]), sp.hstack([Zero, Pcc, Zero]), sp.hstack([Zero, Zero, Pcc])

        self.Pex, self.Pey, self.Pez = self.mesh.getInterpolationMat(self.XYZ_Ex, 'Ex'), self.mesh.getInterpolationMat(self.XYZ_Ey, 'Ey'), self.mesh.getInterpolationMat(self.XYZ_Ez, 'Ez')
        self.Pfx, self.Pfy, self.Pfz = self.mesh.getInterpolationMat(self.XYZ_Fx, 'Fx'), self.mesh.getInterpolationMat(self.XYZ_Fy, 'Fy'), self.mesh.getInterpolationMat(self.XYZ_Fz, 'Fz')

        # Define the source
        # Search over x-faces to find face nearest src_loc
        s_ind = Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fx')
        de = np.zeros(self.mesh.nF, dtype=complex)
        de[s_ind] = 1./self.mesh.hx.min()
        self.de_x = [EM.FDEM.Src.RawVec_e([], self.freq, de/self.mesh.area)]

        self.src_loc_Fx = self.mesh.gridFx[s_ind, :]
        self.src_loc_Fx = self.src_loc_Fx[0]

        # Create survey and problem object
        survey = EM.FDEM.Survey(self.de_x)
        mapping = [('sigma', Maps.IdentityMap(self.mesh)), ('mu', Maps.IdentityMap(self.mesh))]
        problem = EM.FDEM.Problem3D_h(self.mesh, mapping=mapping)

        # Pair problem and survey
        problem.pair(survey)
        problem.Solver = Solver

        # Solve forward problem
        self.numFields_ElecDipole_X = problem.fields(np.r_[SigmaBack, MuBack])

        # setUp_Done = True

    def test_3DMesh_X_ElecDipoleTest_E(self):
        print('Testing E components of a X-oriented analytic harmonic electric dipole.')

        # Specify toleraces
        tol_ElecDipole_X = 4e-2

        # Get E which lives on cell centres
        e_numCC = self.numFields_ElecDipole_X[self.de_x, 'e']

        # Apply data projection matrix to get E at the reciever locations
        ex_num, ey_num, ez_num = self.Pccx*e_numCC, self.Pccy*e_numCC, self.Pccz*e_numCC

        # Get analytic solution
        exa, eya, eza = EM.Analytics.FDEMDipolarfields.E_from_ElectricDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)), orientation='X', kappa= self.kappa)
        exa, eya, eza = Utils.mkvc(exa, 2), Utils.mkvc(eya, 2), Utils.mkvc(eza, 2)

        # Passed?
        passed_x = (np.linalg.norm(exa-ex_num)/np.linalg.norm(exa) <
                    tol_ElecDipole_X)
        passed_y = (np.linalg.norm(eya-ey_num)/np.linalg.norm(eya) <
                    tol_ElecDipole_X)
        passed_z = (np.linalg.norm(eza-ez_num)/np.linalg.norm(eza) <
                    tol_ElecDipole_X)

        passed_x, passed_y, passed_z = errorLog(
            'E', exa, eya, eza, ex_num, ey_num, ez_num, tol
            )

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Ex do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Ey do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Ez do not agree.')

        # Plot Tx and Rx locations on mesh
        if plotIt:

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fx[0], self.src_loc_Fx[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=8)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True,
                                normal="Y", ax = ax)

            # Plot E
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('E', x, exa, eya, eza, ex_num, ey_num, ez_num)

    def test_3DMesh_X_ElecDipoleTest_J(self):
        print('Testing J components of a X-oriented analytic harmonic electric dipole.')
        # Specify toleraces
        tol_ElecDipole_X = 4e-2

        # Get J which lives on faces
        j_numF = self.numFields_ElecDipole_X[self.de_x, 'j']

        # Apply data projection matrix to get J at the reciever locations
        jx_num, jy_num, jz_num = self.Pfx*j_numF, self.Pfy*j_numF, self.Pfz*j_numF

        # Get analytic solution
        jxa, _ , _ = EM.Analytics.FDEMDipolarfields.J_from_ElectricDipoleWholeSpace(self.XYZ_Fx, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        _ , jya , _ = EM.Analytics.FDEMDipolarfields.J_from_ElectricDipoleWholeSpace(self.XYZ_Fy, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        _ , _ , jza = EM.Analytics.FDEMDipolarfields.J_from_ElectricDipoleWholeSpace(self.XYZ_Fz, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        jxa, jya, jza = Utils.mkvc(jxa, 2), Utils.mkvc(jya, 2), Utils.mkvc(jza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'J', jxa, jya, jza, jx_num, jy_num, jz_num, tol_ElecDipole_X
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x_Jx = self.XYZ_Fx[:, 0]
            x_Jy = self.XYZ_Fy[:, 0]
            x_Jz = self.XYZ_Fz[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fx[0], self.src_loc_Fx[2], 'ro', ms=8)
            ax.plot(self.XYZ_Fx[:, 0], self.XYZ_Fx[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fy[:, 0], self.XYZ_Fy[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fz[:, 0], self.XYZ_Fz[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot J
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('J', x, jxa, jya, jza, jx_num, jy_num, jz_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Jx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Jy do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Jz do not agree.')

    def test_3DMesh_X_ElecDipoleTest_H(self):
        print('Testing H components of a X-oriented analytic harmonic electric dipole.')
        # Specify toleraces
        tol_ElecDipole_X = 2e-2

        # Get H which lives on edges
        h_numE = self.numFields_ElecDipole_X[self.de_x, 'h']

        # Apply data projection matrix to get J at the reciever locations
        hx_num, hy_num, hz_num = self.Pex*h_numE, self.Pey*h_numE, self.Pez*h_numE

        # Get analytic solution
        hxa, _ , _  = EM.Analytics.FDEMDipolarfields.H_from_ElectricDipoleWholeSpace(self.XYZ_Ex, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        _ , hya , _ = EM.Analytics.FDEMDipolarfields.H_from_ElectricDipoleWholeSpace(self.XYZ_Ey, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        _ , _ , hza = EM.Analytics.FDEMDipolarfields.H_from_ElectricDipoleWholeSpace(self.XYZ_Ez, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        hxa, hya, hza = Utils.mkvc(hxa, 2), Utils.mkvc(hya, 2), Utils.mkvc(hza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'H', hxa, hya, hza, hx_num, hy_num, hz_num, tol_ElecDipole_X
            )

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Hx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Hy do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Hz do not agree.')

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x_Hx = self.XYZ_Ex[:, 0]
            x_Hy = self.XYZ_Ey[:, 0]
            x_Hz = self.XYZ_Ez[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fx[0], self.src_loc_Fx[2], 'ro', ms=8)
            ax.plot(self.XYZ_Ex[:, 0], self.XYZ_Ex[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ey[:, 0], self.XYZ_Ey[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ez[:, 0], self.XYZ_Ez[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot H
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('H', x, hxa, hya, hza, hx_num, hy_num, hz_num)

    def test_3DMesh_X_ElecDipoleTest_B(self):
        print('Testing B components of a X-oriented analytic harmonic electric dipole.')

        # Specify toleraces
        tol_ElecDipole_X = 2e-2

        # Get E which lives on cell centres
        b_numCC = self.numFields_ElecDipole_X[self.de_x, 'b']

        # Apply data projection matrix to get E at the reciever locations
        bx_num, by_num, bz_num = self.Pccx*b_numCC, self.Pccy*b_numCC, self.Pccz*b_numCC

        # Get analytic solution
        bxa, bya, bza = EM.Analytics.FDEMDipolarfields.B_from_ElectricDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        bxa, bya, bza = Utils.mkvc(bxa, 2), Utils.mkvc(bya, 2), Utils.mkvc(bza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'B', bxa, bya, bza, bx_num, by_num, bz_num, tol_ElecDipole_X
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fx[0], self.src_loc_Fx[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=8)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot B
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('B', x, bxa, bya, bza, bx_num, by_num, bz_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Bx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for By do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Bz do not agree.')

class Y_ElecDipoleTest_3DMesh(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        print('Testing a Y-oriented analytic harmonic electric dipole against the numerical solution on a 3D-tesnsor mesh.')

        # Define model parameters
        self.sigmaback = SIGMABACK
        # mu = mu_0*(1+kappa)
        self.kappa = KAPPA

        # Create 3D mesh
        self.mesh = setUpMesh(npad=9)

        # Set source parameters
        self.freq = 500.
        src_loc = np.r_[0., 0., -35]
        src_loc_CCInd = Utils.closestPoints(self.mesh, src_loc, 'CC')
        self.src_loc_CC = self.mesh.gridCC[src_loc_CCInd,:]
        self.src_loc_CC = self.src_loc_CC[0]

        # Compute skin depth
        skdpth = 500. / np.sqrt(self.sigmaback * self.freq)

        # make sure mesh is big enough
        # print('skin depth =', skdpth)
        # self.assertTrue(self.mesh.hx.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hy.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hz.sum() > skdpth*2.)

        # Create wholespace models
        SigmaBack = self.sigmaback*np.ones((self.mesh.nC))
        MuBack = (mu_0*(1 + self.kappa))*np.ones((self.mesh.nC))

        # Define reciever locations
        xlim = 40. # x locations from -50 to 50
        xInd = np.where(np.abs(self.mesh.vectorCCx) < xlim)
        x = self.mesh.vectorCCx[xInd[0]]
        y = 10.
        z = 30.

        # where we choose to measure
        XYZ = Utils.ndgrid(x, np.r_[y], np.r_[z])

        # Cell centred recievers
        XYZ_CCInd = Utils.closestPoints(self.mesh, XYZ, 'CC')
        self.XYZ_CC = self.mesh.gridCC[XYZ_CCInd,:]

        # Edge recievers
        XYZ_ExInd = Utils.closestPoints(self.mesh, XYZ, 'Ex')
        self.XYZ_Ex = self.mesh.gridEx[XYZ_ExInd,:]
        XYZ_EyInd = Utils.closestPoints(self.mesh, XYZ, 'Ey')
        self.XYZ_Ey = self.mesh.gridEy[XYZ_EyInd,:]
        XYZ_EzInd = Utils.closestPoints(self.mesh, XYZ, 'Ez')
        self.XYZ_Ez = self.mesh.gridEz[XYZ_EzInd,:]

        # Face recievers
        XYZ_FxInd = Utils.closestPoints(self.mesh, XYZ, 'Fx')
        self.XYZ_Fx = self.mesh.gridFx[XYZ_FxInd,:]
        XYZ_FyInd = Utils.closestPoints(self.mesh, XYZ, 'Fy')
        self.XYZ_Fy = self.mesh.gridFy[XYZ_FyInd,:]
        XYZ_FzInd = Utils.closestPoints(self.mesh, XYZ, 'Fz')
        self.XYZ_Fz = self.mesh.gridFz[XYZ_FzInd,:]

        # Form data interpolation matrices
        Pcc = self.mesh.getInterpolationMat(self.XYZ_CC, 'CC')
        Zero = sp.csr_matrix(Pcc.shape)
        self.Pccx, self.Pccy, self.Pccz = sp.hstack([Pcc, Zero, Zero]), sp.hstack([Zero, Pcc, Zero]), sp.hstack([Zero, Zero, Pcc])

        self.Pex, self.Pey, self.Pez = self.mesh.getInterpolationMat(self.XYZ_Ex, 'Ex'), self.mesh.getInterpolationMat(self.XYZ_Ey, 'Ey'), self.mesh.getInterpolationMat(self.XYZ_Ez, 'Ez')
        self.Pfx, self.Pfy, self.Pfz = self.mesh.getInterpolationMat(self.XYZ_Fx, 'Fx'), self.mesh.getInterpolationMat(self.XYZ_Fy, 'Fy'), self.mesh.getInterpolationMat(self.XYZ_Fz, 'Fz')

        # Define the source
        # Search over x-faces to find face nearest src_loc
        s_ind = Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fy') + self.mesh.nFx
        de = np.zeros(self.mesh.nF, dtype=complex)
        de[s_ind] = 1./self.mesh.hy.min()
        self.de_y = [EM.FDEM.Src.RawVec_e([], self.freq, de/self.mesh.area)]

        self.src_loc_Fy = self.mesh.gridFy[Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fy'),:]
        self.src_loc_Fy = self.src_loc_Fy[0]

        # Create survey and problem object
        survey = EM.FDEM.Survey(self.de_y)
        mapping = [('sigma', Maps.IdentityMap(self.mesh)), ('mu', Maps.IdentityMap(self.mesh))]
        problem = EM.FDEM.Problem3D_h(self.mesh, mapping=mapping)

        # Pair problem and survey
        problem.pair(survey)
        problem.Solver = Solver

        # Solve forward problem
        self.numFields_ElecDipole_Y = problem.fields(np.r_[SigmaBack, MuBack])

        # setUp_Done = True

    def test_3DMesh_Y_ElecDipoleTest_E(self):
        print('Testing E components of a Y-oriented analytic harmonic electric dipole.')

        # Specify toleraces
        tol_ElecDipole_Y = 4e-2

        # Get E which lives on cell centres
        e_numCC = self.numFields_ElecDipole_Y[self.de_y, 'e']

        # Apply data projection matrix to get E at the reciever locations
        ex_num, ey_num, ez_num = self.Pccx*e_numCC, self.Pccy*e_numCC, self.Pccz*e_numCC

        # Get analytic solution
        exa, eya, eza = EM.Analytics.FDEMDipolarfields.E_from_ElectricDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)), orientation='Y', kappa= self.kappa)
        exa, eya, eza = Utils.mkvc(exa, 2), Utils.mkvc(eya, 2), Utils.mkvc(eza, 2)

        passed_x = (np.linalg.norm(exa-ex_num)/np.linalg.norm(exa) <
                    tol_ElecDipole_Y)
        passed_y = (np.linalg.norm(eya-ey_num)/np.linalg.norm(eya) <
                    tol_ElecDipole_Y)
        passed_z = (np.linalg.norm(eza-ez_num)/np.linalg.norm(eza) <
                    tol_ElecDipole_Y)

        passed_x, passed_y, passed_z = errorLog(
            'E', exa, eya, eza, ex_num, ey_num, ez_num, tol
            )

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Ex do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Ey do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Ez do not agree.')

        # Plot Tx and Rx locations on mesh
        if plotIt:

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fy[0], self.src_loc_Fy[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=8)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)


            # Plot E
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('E', x, exa, eya, eza, ex_num, ey_num, ez_num)

    def test_3DMesh_Y_ElecDipoleTest_J(self):
        print('Testing J components of a Y-oriented analytic harmonic electric dipole.')
        # Specify toleraces
        tol_ElecDipole_Y = 4e-2

        # Get J which lives on faces
        j_numF = self.numFields_ElecDipole_Y[self.de_y, 'j']

        # Apply data projection matrix to get J at the reciever locations
        jx_num, jy_num, jz_num = self.Pfx*j_numF, self.Pfy*j_numF, self.Pfz*j_numF

        # Get analytic solution
        jxa, _ , _ = EM.Analytics.FDEMDipolarfields.J_from_ElectricDipoleWholeSpace(self.XYZ_Fx, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        _ , jya , _ = EM.Analytics.FDEMDipolarfields.J_from_ElectricDipoleWholeSpace(self.XYZ_Fy, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        _ , _ , jza = EM.Analytics.FDEMDipolarfields.J_from_ElectricDipoleWholeSpace(self.XYZ_Fz, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        jxa, jya, jza = Utils.mkvc(jxa, 2), Utils.mkvc(jya, 2), Utils.mkvc(jza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'J', jxa, jya, jza, jx_num, jy_num, jz_num, tol_ElecDipole_Y
            )

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Jx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Jy do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Jz do not agree.')
        # Plot Tx and Rx locations on mesY
        if plotIt:

            x_Jx = self.XYZ_Fx[:, 0]
            x_Jy = self.XYZ_Fy[:, 0]
            x_Jz = self.XYZ_Fz[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fy[0], self.src_loc_Fy[2], 'ro', ms=8)
            ax.plot(self.XYZ_Fx[:, 0], self.XYZ_Fx[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fy[:, 0], self.XYZ_Fy[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fz[:, 0], self.XYZ_Fz[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot H
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('H', x, hxa, hya, hza, hx_num, hy_num, hz_num)

    def test_3DMesh_Y_ElecDipoleTest_H(self):
        print('Testing H components of a Y-oriented analytic harmonic electric dipole.')
        # Specify toleraces
        tol_ElecDipole_Y = 2e-2

        # Get H which lives on edges
        h_numE = self.numFields_ElecDipole_Y[self.de_y, 'h']

        # Apply data projection matrix to get J at the reciever locations
        hx_num, hy_num, hz_num = self.Pex*h_numE, self.Pey*h_numE, self.Pez*h_numE

        # Get analytic solution
        hxa, _ , _  = EM.Analytics.FDEMDipolarfields.H_from_ElectricDipoleWholeSpace(self.XYZ_Ex, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        _ , hya , _ = EM.Analytics.FDEMDipolarfields.H_from_ElectricDipoleWholeSpace(self.XYZ_Ey, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        _ , _ , hza = EM.Analytics.FDEMDipolarfields.H_from_ElectricDipoleWholeSpace(self.XYZ_Ez, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        hxa, hya, hza = Utils.mkvc(hxa, 2), Utils.mkvc(hya, 2), Utils.mkvc(hza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'H', hxa, hya, hza, hx_num, hy_num, hz_num, tol_ElecDipole_Y
            )


        # Plot Tx and Rx locations on mesh
        if plotIt:

            x_Hx = self.XYZ_Ex[:, 0]
            x_Hy = self.XYZ_Ey[:, 0]
            x_Hz = self.XYZ_Ez[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fy[0], self.src_loc_Fy[2], 'ro', ms=8)
            ax.plot(self.XYZ_Ex[:, 0], self.XYZ_Ex[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ey[:, 0], self.XYZ_Ey[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ez[:, 0], self.XYZ_Ez[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot J
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('J', x, jxa, jya, jza, jx_num, jy_num, jz_num)

        self.assertTrue(
            passed_x, msg='Analytic and numeric solutions for Hx do not agree.'
            )
        self.assertTrue(
            passed_y, msg='Analytic and numeric solutions for Hy do not agree.'
            )
        self.assertTrue(
            passed_z, msg='Analytic and numeric solutions for Hz do not agree.'
            )

    def test_3DMesh_Y_ElecDipoleTest_B(self):
        print('Testing B components of a Y-oriented analytic harmonic electric dipole.')

        # Specify toleraces
        tol_ElecDipole_Y = 2e-2

        # Get E which lives on cell centres
        b_numCC = self.numFields_ElecDipole_Y[self.de_y, 'b']

        # Apply data projection matrix to get E at the reciever locations
        bx_num, by_num, bz_num = self.Pccx*b_numCC, self.Pccy*b_numCC, self.Pccz*b_numCC

        # Get analytic solution
        bxa, bya, bza = EM.Analytics.FDEMDipolarfields.B_from_ElectricDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        bxa, bya, bza = Utils.mkvc(bxa, 2), Utils.mkvc(bya, 2), Utils.mkvc(bza, 2)

        passed_x = (np.linalg.norm(bxa-bx_num)/np.linalg.norm(bxa) <
                    tol_ElecDipole_Y)
        passed_y = (np.linalg.norm(bya-by_num) < tol_NumErrZero)
        passed_z = (np.linalg.norm(bza-bz_num)/np.linalg.norm(bza) <
                    tol_ElecDipole_Y)

        passed_x, passed_y, passed_z = errorLog(
            'B', bxa, bya, bza, bx_num, by_num, bz_num, tol
            )

        self.assertTrue(
            passed_x, msg='Analytic and numeric solutions for Jx do not agree.'
            )
        self.assertTrue(
            passed_y, msg='Analytic and numeric solutions for Jy do not agree.'
            )
        self.assertTrue(
            passed_z, msg='Analytic and numeric solutions for Jz do not agree.'
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fy[0], self.src_loc_Fy[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=8)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot B
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('B', x, bxa, bya, bza, bx_num, by_num, bz_num)


class Z_ElecDipoleTest_3DMesh(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        print('Testing a Z-oriented analytic harmonic electric dipole against the numerical solution on a 3D-tesnsor mesh.')

        # Define model parameters
        self.sigmaback = SIGMABACK
        # mu = mu_0*(1+kappa)
        self.kappa = KAPPA

        # Create 3D mesh
        self.mesh = setUpMesh()

        # Set source parameters
        self.freq = 500.
        src_loc = np.r_[0., 0., -35]
        src_loc_CCInd = Utils.closestPoints(self.mesh, src_loc, 'CC')
        self.src_loc_CC = self.mesh.gridCC[src_loc_CCInd,:]
        self.src_loc_CC = self.src_loc_CC[0]

        # Compute skin depth
        skdpth = 500. / np.sqrt(self.sigmaback * self.freq)

        # make sure mesh is big enough
        # print('skin depth =', skdpth)
        # self.assertTrue(self.mesh.hx.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hy.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hz.sum() > skdpth*2.)

        # Create wholespace models
        SigmaBack = self.sigmaback*np.ones((self.mesh.nC))
        MuBack = (mu_0*(1 + self.kappa))*np.ones((self.mesh.nC))

        # Define reciever locations
        xlim = 40. # x locations from -50 to 50
        xInd = np.where(np.abs(self.mesh.vectorCCx) < xlim)
        x = self.mesh.vectorCCx[xInd[0]]
        y = 10.
        z = 30.

        # where we choose to measure
        XYZ = Utils.ndgrid(x, np.r_[y], np.r_[z])

        # Cell centred recievers
        XYZ_CCInd = Utils.closestPoints(self.mesh, XYZ, 'CC')
        self.XYZ_CC = self.mesh.gridCC[XYZ_CCInd,:]

        # Edge recievers
        XYZ_ExInd = Utils.closestPoints(self.mesh, XYZ, 'Ex')
        self.XYZ_Ex = self.mesh.gridEx[XYZ_ExInd,:]
        XYZ_EyInd = Utils.closestPoints(self.mesh, XYZ, 'Ey')
        self.XYZ_Ey = self.mesh.gridEy[XYZ_EyInd,:]
        XYZ_EzInd = Utils.closestPoints(self.mesh, XYZ, 'Ez')
        self.XYZ_Ez = self.mesh.gridEz[XYZ_EzInd,:]

        # Face recievers
        XYZ_FxInd = Utils.closestPoints(self.mesh, XYZ, 'Fx')
        self.XYZ_Fx = self.mesh.gridFx[XYZ_FxInd,:]
        XYZ_FyInd = Utils.closestPoints(self.mesh, XYZ, 'Fy')
        self.XYZ_Fy = self.mesh.gridFy[XYZ_FyInd,:]
        XYZ_FzInd = Utils.closestPoints(self.mesh, XYZ, 'Fz')
        self.XYZ_Fz = self.mesh.gridFz[XYZ_FzInd,:]

        # Form data interpolation matrices
        Pcc = self.mesh.getInterpolationMat(self.XYZ_CC, 'CC')
        Zero = sp.csr_matrix(Pcc.shape)
        self.Pccx, self.Pccy, self.Pccz = sp.hstack([Pcc, Zero, Zero]), sp.hstack([Zero, Pcc, Zero]), sp.hstack([Zero, Zero, Pcc])

        self.Pex, self.Pey, self.Pez = self.mesh.getInterpolationMat(self.XYZ_Ex, 'Ex'), self.mesh.getInterpolationMat(self.XYZ_Ey, 'Ey'), self.mesh.getInterpolationMat(self.XYZ_Ez, 'Ez')
        self.Pfx, self.Pfy, self.Pfz = self.mesh.getInterpolationMat(self.XYZ_Fx, 'Fx'), self.mesh.getInterpolationMat(self.XYZ_Fy, 'Fy'), self.mesh.getInterpolationMat(self.XYZ_Fz, 'Fz')

        # Define the source
        # Search over x-faces to find face nearest src_loc
        s_ind = Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fz') + self.mesh.nFx + self.mesh.nFy
        de = np.zeros(self.mesh.nF, dtype=complex)
        de[s_ind] = 1./self.mesh.hz.min()
        self.de_z = [EM.FDEM.Src.RawVec_e([], self.freq, de/self.mesh.area)]

        self.src_loc_Fz = self.mesh.gridFz[Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fz'),:]
        self.src_loc_Fz = self.src_loc_Fz[0]

        # Create survey and problem object
        survey = EM.FDEM.Survey(self.de_z)
        mapping = [('sigma', Maps.IdentityMap(self.mesh)), ('mu', Maps.IdentityMap(self.mesh))]
        problem = EM.FDEM.Problem3D_h(self.mesh, mapping=mapping)

        # Pair problem and survey
        problem.pair(survey)
        problem.Solver = Solver

        # Solve forward problem
        self.numFields_ElecDipole_Z = problem.fields(np.r_[SigmaBack, MuBack])

        # setUp_Done = True

    def test_3DMesh_Z_ElecDipoleTest_E(self):
        print('Testing E components of a Z-oriented analytic harmonic electric dipole.')

        # Specify toleraces
        tol_ElecDipole_Z = 2e-2

        # Get E which lives on cell centres
        e_numCC = self.numFields_ElecDipole_Z[self.de_z, 'e']

        # Apply data projection matrix to get E at the reciever locations
        ex_num, ey_num, ez_num = self.Pccx*e_numCC, self.Pccy*e_numCC, self.Pccz*e_numCC

        # Get analytic solution
        exa, eya, eza = EM.Analytics.FDEMDipolarfields.E_from_ElectricDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)), orientation='Z', kappa= self.kappa)
        exa, eya, eza = Utils.mkvc(exa, 2), Utils.mkvc(eya, 2), Utils.mkvc(eza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'B', exa, eya, eza, ex_num, ey_num, ez_num, tol_ElecDipole_Z
            )

        self.assertTrue(
            passed_x, msg='Analytic and numeric solutions for Ex do not agree.'
            )
        self.assertTrue(
            passed_y, msg='Analytic and numeric solutions for Ey do not agree.'
            )
        self.assertTrue(
            passed_z, msg='Analytic and numeric solutions for Ez do not agree.'
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fz[0], self.src_loc_Fz[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=8)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot E
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('E', x, exa, eya, eza, ex_num, ey_num, ez_num)

    def test_3DMesh_Z_ElecDipoleTest_J(self):
        print('Testing J components of a Z-oriented analytic harmonic electric dipole.')
        # Specify toleraces
        tol_ElecDipole_Z = 2e-2

        # Get J which lives on faces
        j_numF = self.numFields_ElecDipole_Z[self.de_z, 'j']

        # Apply data projection matrix to get J at the reciever locations
        jx_num, jy_num, jz_num = self.Pfx*j_numF, self.Pfy*j_numF, self.Pfz*j_numF

        # Get analytic solution
        jxa, _ , _ = EM.Analytics.FDEMDipolarfields.J_from_ElectricDipoleWholeSpace(self.XYZ_Fx, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        _ , jya , _ = EM.Analytics.FDEMDipolarfields.J_from_ElectricDipoleWholeSpace(self.XYZ_Fy, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        _ , _ , jza = EM.Analytics.FDEMDipolarfields.J_from_ElectricDipoleWholeSpace(self.XYZ_Fz, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        jxa, jya, jza = Utils.mkvc(jxa, 2), Utils.mkvc(jya, 2), Utils.mkvc(jza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'J', jxa, jya, jza, jx_num, jy_num, jz_num, tol_ElecDipole_Z
            )

        # Plot Tx and Rx locations on mesY
        if plotIt:

            x_Jx = self.XYZ_Fx[:, 0]
            x_Jy = self.XYZ_Fy[:, 0]
            x_Jz = self.XYZ_Fz[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fz[0], self.src_loc_Fz[2], 'ro', ms=8)
            ax.plot(self.XYZ_Fx[:, 0], self.XYZ_Fx[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fy[:, 0], self.XYZ_Fy[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fz[:, 0], self.XYZ_Fz[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot J
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('J', x, jxa, jya, jza, jx_num, jy_num, jz_num)

        self.assertTrue(
            passed_x, msg='Analytic and numeric solutions for Jx do not agree.'
            )
        self.assertTrue(
            passed_y, msg='Analytic and numeric solutions for Jy do not agree.'
            )
        self.assertTrue(
            passed_z, msg='Analytic and numeric solutions for Jz do not agree.'
            )

    def test_3DMesh_Z_ElecDipoleTest_H(self):
        print('Testing H components of a Z-oriented analytic harmonic electric dipole.')
        # Specify toleraces
        tol_ElecDipole_Z = 2e-2

        # Get H which lives on edges
        h_numE = self.numFields_ElecDipole_Z[self.de_z, 'h']

        # Apply data projection matrix to get J at the reciever locations
        hx_num, hy_num, hz_num = self.Pex*h_numE, self.Pey*h_numE, self.Pez*h_numE

        # Get analytic solution
        hxa, _ , _  = EM.Analytics.FDEMDipolarfields.H_from_ElectricDipoleWholeSpace(self.XYZ_Ex, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        _ , hya , _ = EM.Analytics.FDEMDipolarfields.H_from_ElectricDipoleWholeSpace(self.XYZ_Ey, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        _ , _ , hza = EM.Analytics.FDEMDipolarfields.H_from_ElectricDipoleWholeSpace(self.XYZ_Ez, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        hxa, hya, hza = Utils.mkvc(hxa, 2), Utils.mkvc(hya, 2), Utils.mkvc(hza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'H', hxa, hya, hza, hx_num, hy_num, hz_num, tol_ElecDipole_Z
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x_Hx = self.XYZ_Ex[:, 0]
            x_Hy = self.XYZ_Ey[:, 0]
            x_Hz = self.XYZ_Ez[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fz[0], self.src_loc_Fz[2], 'ro', ms=8)
            ax.plot(self.XYZ_Ex[:, 0], self.XYZ_Ex[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ey[:, 0], self.XYZ_Ey[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ez[:, 0], self.XYZ_Ez[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot H
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('H', x, hxa, hya, hza, hx_num, hy_num, hz_num)

        self.assertTrue(
            passed_x, msg='Analytic and numeric solutions for Jx do not agree.'
            )
        self.assertTrue(
            passed_y, msg='Analytic and numeric solutions for Jy do not agree.'
            )
        self.assertTrue(
            passed_z, msg='Analytic and numeric solutions for Jz do not agree.'
            )

    def test_3DMesh_Z_ElecDipoleTest_B(self):
        print('Testing B components of a Z-oriented analytic harmonic electric dipole.')

        # Specify toleraces
        tol_ElecDipole_Z = 2e-2

        # Get E which lives on cell centres
        b_numCC = self.numFields_ElecDipole_Z[self.de_z, 'b']

        # Apply data projection matrix to get E at the reciever locations
        bx_num, by_num, bz_num = self.Pccx*b_numCC, self.Pccy*b_numCC, self.Pccz*b_numCC

        # Get analytic solution
        bxa, bya, bza = EM.Analytics.FDEMDipolarfields.B_from_ElectricDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        bxa, bya, bza = Utils.mkvc(bxa, 2), Utils.mkvc(bya, 2), Utils.mkvc(bza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'B', bxa, bya, bza, bx_num, by_num, bz_num, tol_ElecDipole_Z
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fz[0], self.src_loc_Fz[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=8)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot B
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('B', x, bxa, bya, bza, bx_num, by_num, bz_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Bx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for By do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Bz do not agree.')

class X_MaDipoleTest_3DMesh(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        print('Testing a X-oriented analytic harmonic magnetic dipole against the numerical solution on a 3D-tesnsor mesh.')

        # Define model parameters
        self.sigmaback = SIGMABACK
        # mu = mu_0*(1+kappa)
        self.kappa = KAPPA

        # Create 3D mesh
        self.mesh = setUpMesh()

        # Set source parameters
        self.freq = 500.
        src_loc = np.r_[0., 0., -35]
        src_loc_CCInd = Utils.closestPoints(self.mesh, src_loc, 'CC')
        self.src_loc_CC = self.mesh.gridCC[src_loc_CCInd,:]
        self.src_loc_CC = self.src_loc_CC[0]

        # Compute skin depth
        skdpth = 500. / np.sqrt(self.sigmaback * self.freq)

        # make sure mesh is big enough
        # print('skin depth =', skdpth)
        # self.assertTrue(self.mesh.hx.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hy.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hz.sum() > skdpth*2.)

        # Create wholespace models
        SigmaBack = self.sigmaback*np.ones((self.mesh.nC))
        MuBack = (mu_0*(1 + self.kappa))*np.ones((self.mesh.nC))

        # Define reciever locations
        xlim = 40. # x locations from -50 to 50
        xInd = np.where(np.abs(self.mesh.vectorCCx) < xlim)
        x = self.mesh.vectorCCx[xInd[0]]
        y = 10.
        z = 30.

        # where we choose to measure
        XYZ = Utils.ndgrid(x, np.r_[y], np.r_[z])

        # Cell centred recievers
        XYZ_CCInd = Utils.closestPoints(self.mesh, XYZ, 'CC')
        self.XYZ_CC = self.mesh.gridCC[XYZ_CCInd,:]

        # Edge recievers
        XYZ_ExInd = Utils.closestPoints(self.mesh, XYZ, 'Ex')
        self.XYZ_Ex = self.mesh.gridEx[XYZ_ExInd,:]
        XYZ_EyInd = Utils.closestPoints(self.mesh, XYZ, 'Ey')
        self.XYZ_Ey = self.mesh.gridEy[XYZ_EyInd,:]
        XYZ_EzInd = Utils.closestPoints(self.mesh, XYZ, 'Ez')
        self.XYZ_Ez = self.mesh.gridEz[XYZ_EzInd,:]

        # Face recievers
        XYZ_FxInd = Utils.closestPoints(self.mesh, XYZ, 'Fx')
        self.XYZ_Fx = self.mesh.gridFx[XYZ_FxInd,:]
        XYZ_FyInd = Utils.closestPoints(self.mesh, XYZ, 'Fy')
        self.XYZ_Fy = self.mesh.gridFy[XYZ_FyInd,:]
        XYZ_FzInd = Utils.closestPoints(self.mesh, XYZ, 'Fz')
        self.XYZ_Fz = self.mesh.gridFz[XYZ_FzInd,:]

        # Form data interpolation matrices
        Pcc = self.mesh.getInterpolationMat(self.XYZ_CC, 'CC')
        Zero = sp.csr_matrix(Pcc.shape)
        self.Pccx, self.Pccy, self.Pccz = sp.hstack([Pcc, Zero, Zero]), sp.hstack([Zero, Pcc, Zero]), sp.hstack([Zero, Zero, Pcc])

        self.Pex, self.Pey, self.Pez = self.mesh.getInterpolationMat(self.XYZ_Ex, 'Ex'), self.mesh.getInterpolationMat(self.XYZ_Ey, 'Ey'), self.mesh.getInterpolationMat(self.XYZ_Ez, 'Ez')
        self.Pfx, self.Pfy, self.Pfz = self.mesh.getInterpolationMat(self.XYZ_Fx, 'Fx'), self.mesh.getInterpolationMat(self.XYZ_Fy, 'Fy'), self.mesh.getInterpolationMat(self.XYZ_Fz, 'Fz')

        # Define the source
        # Search over x-faces to find face nearest src_loc
        s_ind = Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fx')
        dm = np.zeros(self.mesh.nF, dtype=complex)
        dm[s_ind] = (-1j*(2*np.pi*self.freq)*(mu_0*(1 + self.kappa)))/self.mesh.hx.min()
        self.dm_x = [EM.FDEM.Src.RawVec_m([], self.freq, dm/self.mesh.area)]

        self.src_loc_Fx = self.mesh.gridFx[Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fx'),:]
        self.src_loc_Fx = self.src_loc_Fx[0]

        # Create survey and problem object
        survey = EM.FDEM.Survey(self.dm_x)
        mapping = [('sigma', Maps.IdentityMap(self.mesh)), ('mu', Maps.IdentityMap(self.mesh))]
        problem = EM.FDEM.Problem3D_b(self.mesh, mapping=mapping)

        # Pair problem and survey
        problem.pair(survey)
        problem.Solver = Solver

        # Solve forward problem
        self.numFields_MagDipole_X = problem.fields(np.r_[SigmaBack, MuBack])

        # setUp_Done = True

    def test_3DMesh_X_MagDipoleTest_E(self):
        print('Testing E components of a X-oriented analytic harmonic magnetic dipole.')

        # Specify toleraces
        tol_MagDipole_X = 2e-2

        # Get E which lives on edges
        e_numE = self.numFields_MagDipole_X[self.dm_x, 'e']

        # Apply data projection matrix to get E at the reciever locations
        ex_num, ey_num, ez_num = self.Pex*e_numE, self.Pey*e_numE, self.Pez*e_numE

        # Get analytic solution
        exa, _ , _  = EM.Analytics.FDEMDipolarfields.E_from_MagneticDipoleWholeSpace(self.XYZ_Ex, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        _ , eya , _ = EM.Analytics.FDEMDipolarfields.E_from_MagneticDipoleWholeSpace(self.XYZ_Ey, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        _ , _ , eza = EM.Analytics.FDEMDipolarfields.E_from_MagneticDipoleWholeSpace(self.XYZ_Ez, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        exa, eya, eza = Utils.mkvc(exa, 2), Utils.mkvc(eya, 2), Utils.mkvc(eza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'E', exa, eya, eza, ex_num, ey_num, ez_num, tol_MagDipole_X
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x_Ex = self.XYZ_Ex[:, 0]
            x_Ey = self.XYZ_Ey[:, 0]
            x_Ez = self.XYZ_Ez[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fx[0], self.src_loc_Fx[2], 'ro', ms=8)
            ax.plot(self.XYZ_Ex[:, 0], self.XYZ_Ex[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ey[:, 0], self.XYZ_Ey[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ez[:, 0], self.XYZ_Ez[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot E
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('E', x, exa, eya, eza, ex_num, ey_num, ez_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Ex do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Ey do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Ez do not agree.')

    def test_3DMesh_X_MagDipoleTest_J(self):
        print('Testing J components of a X-oriented analytic harmonic magnetic dipole.')
        # Specify toleraces
        tol_MagDipole_X = 2e-2

        # Get J which lives on faces
        j_numCC = self.numFields_MagDipole_X[self.dm_x, 'j']

        # Apply data projection matrix to get J at the reciever locations
        jx_num, jy_num, jz_num = self.Pccx*j_numCC, self.Pccy*j_numCC, self.Pccz*j_numCC

        # Get analytic solution
        jxa, jya, jza = EM.Analytics.FDEMDipolarfields.J_from_MagneticDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        jxa, jya, jza = Utils.mkvc(jxa, 2), Utils.mkvc(jya, 2), Utils.mkvc(jza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'J', jxa, jya, jza, jx_num, jy_num, jz_num, tol_MagDipole_X
            )

        # Plot Tx and Rx locations on mesY
        if plotIt:

            x = self.XYZ_CC[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fx[0], self.src_loc_Fx[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot J
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('J', x, jxa, jya, jza, jx_num, jy_num, jz_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Jx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Jy do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Jz do not agree.')

    def test_3DMesh_X_MagDipoleTest_H(self):
        print('Testing H components of a X-oriented analytic harmonic magnetic dipole.')
        # Specify toleraces
        tol_MagDipole_X = 4e-2

        # Get H which lives on edges
        h_numCC = self.numFields_MagDipole_X[self.dm_x, 'h']

        # Apply data projection matrix to get J at the reciever locations
        hx_num, hy_num, hz_num = self.Pccx*h_numCC, self.Pccy*h_numCC, self.Pccz*h_numCC

        # Get analytic solution
        hxa, hya, hza = EM.Analytics.FDEMDipolarfields.H_from_MagneticDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        hxa, hya, hza = Utils.mkvc(hxa, 2), Utils.mkvc(hya, 2), Utils.mkvc(hza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'H', hxa, hya, hza, hx_num, hy_num, hz_num, tol_MagDipole_X
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x = self.XYZ_CC[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fx[0], self.src_loc_Fx[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot H
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('H', x, hxa, hya, hza, hx_num, hy_num, hz_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Hx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Hy do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Hz do not agree.')


    def test_3DMesh_X_MagDipoleTest_B(self):
        print('Testing B components of a X-oriented analytic harmonic magnetic dipole.')

        # Specify toleraces
        tol_MagDipole_X = 4e-2

        # Get E which lives on cell centres
        b_numF = self.numFields_MagDipole_X[self.dm_x, 'b']

        # Apply data projection matrix to get E at the reciever locations
        bx_num, by_num, bz_num = self.Pfx*b_numF, self.Pfy*b_numF, self.Pfz*b_numF

        # Get analytic solution
        bxa, _ , _  = EM.Analytics.FDEMDipolarfields.B_from_MagneticDipoleWholeSpace(self.XYZ_Fx, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        _ , bya , _ = EM.Analytics.FDEMDipolarfields.B_from_MagneticDipoleWholeSpace(self.XYZ_Fy, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        _ , _ , bza = EM.Analytics.FDEMDipolarfields.B_from_MagneticDipoleWholeSpace(self.XYZ_Fz, self.src_loc_Fx, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='X',kappa= self.kappa)
        bxa, bya, bza = Utils.mkvc(bxa, 2), Utils.mkvc(bya, 2), Utils.mkvc(bza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'B', bxa, bya, bza, bx_num, by_num, bz_num, tol_MagDipole_X
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x_Bx = self.XYZ_Fx[:, 0]
            x_By = self.XYZ_Fy[:, 0]
            x_Bz = self.XYZ_Fz[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fx[0], self.src_loc_Fx[2], 'ro', ms=8)
            ax.plot(self.XYZ_Fx[:, 0], self.XYZ_Fx[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fy[:, 0], self.XYZ_Fy[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fz[:, 0], self.XYZ_Fz[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot E
            fig, ax = plt.subplots(2, 3, figsize=(20, 10))

            plotLine_num_ana(ax[0], x_Bx, bx_num.real, bxa.real,
                             title='B_x Real')
            plotLine_num_ana(ax[1], x_Bx, bx_num.imag, bxa.imag,
                             title='B_x Imag')

            plotLine_num_ana(ax[2], x_By, by_num.real, bya.real,
                             title='B_y Real')
            plotLine_num_ana(ax[3], x_By, by_num.imag, bya.imag,
                             title='B_y Imag')

            plotLine_num_ana(ax[4], x_Bz, bz_num.real, bza.real,
                             title='B_z Real')
            plotLine_num_ana(ax[5], x_Bz, bz_num.imag, bza.imag,
                             title='B_z Imag')

            plt.legend(['Num', 'Ana'], bbox_to_anchor=(1.5, 0.5))
            plt.tight_layout()
            plt.show()

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Bx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for By do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Bz do not agree.')


class Y_MaDipoleTest_3DMesh(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        print('Testing a Y-oriented analytic harmonic magnetic dipole against the numerical solution on a 3D-tesnsor mesh.')

        # Define model parameters
        self.sigmaback = SIGMABACK
        # mu = mu_0*(1+kappa)
        self.kappa = KAPPA

        # Create 3D mesh
        self.mesh = setUpMesh()

        # Set source parameters
        self.freq = 500.
        src_loc = np.r_[0., 0., -35]
        src_loc_CCInd = Utils.closestPoints(self.mesh, src_loc, 'CC')
        self.src_loc_CC = self.mesh.gridCC[src_loc_CCInd,:]
        self.src_loc_CC = self.src_loc_CC[0]

        # Compute skin depth
        skdpth = 500. / np.sqrt(self.sigmaback * self.freq)

        # make sure mesh is big enough
        # print('skin depth =', skdpth)
        # self.assertTrue(self.mesh.hx.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hy.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hz.sum() > skdpth*2.)

        # Create wholespace models
        SigmaBack = self.sigmaback*np.ones((self.mesh.nC))
        MuBack = (mu_0*(1 + self.kappa))*np.ones((self.mesh.nC))

        # Define reciever locations
        xlim = 40. # x locations from -50 to 50
        xInd = np.where(np.abs(self.mesh.vectorCCx) < xlim)
        x = self.mesh.vectorCCx[xInd[0]]
        y = 10.
        z = 30.

        # where we choose to measure
        XYZ = Utils.ndgrid(x, np.r_[y], np.r_[z])

        # Cell centred recievers
        XYZ_CCInd = Utils.closestPoints(self.mesh, XYZ, 'CC')
        self.XYZ_CC = self.mesh.gridCC[XYZ_CCInd,:]

        # Edge recievers
        XYZ_ExInd = Utils.closestPoints(self.mesh, XYZ, 'Ex')
        self.XYZ_Ex = self.mesh.gridEx[XYZ_ExInd,:]
        XYZ_EyInd = Utils.closestPoints(self.mesh, XYZ, 'Ey')
        self.XYZ_Ey = self.mesh.gridEy[XYZ_EyInd,:]
        XYZ_EzInd = Utils.closestPoints(self.mesh, XYZ, 'Ez')
        self.XYZ_Ez = self.mesh.gridEz[XYZ_EzInd,:]

        # Face recievers
        XYZ_FxInd = Utils.closestPoints(self.mesh, XYZ, 'Fx')
        self.XYZ_Fx = self.mesh.gridFx[XYZ_FxInd,:]
        XYZ_FyInd = Utils.closestPoints(self.mesh, XYZ, 'Fy')
        self.XYZ_Fy = self.mesh.gridFy[XYZ_FyInd,:]
        XYZ_FzInd = Utils.closestPoints(self.mesh, XYZ, 'Fz')
        self.XYZ_Fz = self.mesh.gridFz[XYZ_FzInd,:]

        # Form data interpolation matrices
        Pcc = self.mesh.getInterpolationMat(self.XYZ_CC, 'CC')
        Zero = sp.csr_matrix(Pcc.shape)
        self.Pccx, self.Pccy, self.Pccz = sp.hstack([Pcc, Zero, Zero]), sp.hstack([Zero, Pcc, Zero]), sp.hstack([Zero, Zero, Pcc])

        self.Pex, self.Pey, self.Pez = self.mesh.getInterpolationMat(self.XYZ_Ex, 'Ex'), self.mesh.getInterpolationMat(self.XYZ_Ey, 'Ey'), self.mesh.getInterpolationMat(self.XYZ_Ez, 'Ez')
        self.Pfx, self.Pfy, self.Pfz = self.mesh.getInterpolationMat(self.XYZ_Fx, 'Fx'), self.mesh.getInterpolationMat(self.XYZ_Fy, 'Fy'), self.mesh.getInterpolationMat(self.XYZ_Fz, 'Fz')

        # Define the source
        # Search over x-faces to find face nearest src_loc
        s_ind = Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fy') + self.mesh.nFx
        dm = np.zeros(self.mesh.nF, dtype=complex)
        dm[s_ind] = (-1j*(2*np.pi*self.freq)*(mu_0*(1 + self.kappa)))/self.mesh.hy.min()
        self.dm_y = [EM.FDEM.Src.RawVec_m([], self.freq, dm/self.mesh.area)]

        self.src_loc_Fy = self.mesh.gridFy[Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fy'),:]
        self.src_loc_Fy = self.src_loc_Fy[0]

        # Create survey and problem object
        survey = EM.FDEM.Survey(self.dm_y)
        mapping = [('sigma', Maps.IdentityMap(self.mesh)), ('mu', Maps.IdentityMap(self.mesh))]
        problem = EM.FDEM.Problem3D_b(self.mesh, mapping=mapping)

        # Pair problem and survey
        problem.pair(survey)
        problem.Solver = Solver

        # Solve forward problem
        self.numFields_MagDipole_Y = problem.fields(np.r_[SigmaBack, MuBack])

        # setUp_Done = True

    def test_3DMesh_Y_MagDipoleTest_E(self):
        print('Testing E components of a Y-oriented analytic harmonic magnetic dipole.')

        # Specify toleraces
        tol_MagDipole_Y = 2e-2

        # Get E which lives on edges
        e_numE = self.numFields_MagDipole_Y[self.dm_y, 'e']

        # Apply data projection matrix to get E at the reciever locations
        ex_num, ey_num, ez_num = self.Pex*e_numE, self.Pey*e_numE, self.Pez*e_numE

        # Get analytic solution
        exa, _ , _  = EM.Analytics.FDEMDipolarfields.E_from_MagneticDipoleWholeSpace(self.XYZ_Ex, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        _ , eya , _ = EM.Analytics.FDEMDipolarfields.E_from_MagneticDipoleWholeSpace(self.XYZ_Ey, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        _ , _ , eza = EM.Analytics.FDEMDipolarfields.E_from_MagneticDipoleWholeSpace(self.XYZ_Ez, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        exa, eya, eza = Utils.mkvc(exa, 2), Utils.mkvc(eya, 2), Utils.mkvc(eza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'E', exa, eya, eza, ex_num, ey_num, ez_num, tol_MagDipole_Y
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x_Ex = self.XYZ_Ex[:, 0]
            x_Ey = self.XYZ_Ey[:, 0]
            x_Ez = self.XYZ_Ez[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fy[0], self.src_loc_Fy[2], 'ro', ms=8)
            ax.plot(self.XYZ_Ex[:, 0], self.XYZ_Ex[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ey[:, 0], self.XYZ_Ey[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ez[:, 0], self.XYZ_Ez[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot E
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('E', x, exa, eya, eza, ex_num, ey_num, ez_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Ex do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Ey do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Ez do not agree.')

    def test_3DMesh_Y_MagDipoleTest_J(self):
        print('Testing J components of a Y-oriented analytic harmonic magnetic dipole.')
        # Specify toleraces
        tol_MagDipole_Y = 2e-2

        # Get J which lives on faces
        j_numCC = self.numFields_MagDipole_Y[self.dm_y, 'j']

        # Apply data projection matrix to get J at the reciever locations
        jx_num, jy_num, jz_num = self.Pccx*j_numCC, self.Pccy*j_numCC, self.Pccz*j_numCC

        # Get analytic solution
        jxa, jya, jza = EM.Analytics.FDEMDipolarfields.J_from_MagneticDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        jxa, jya, jza = Utils.mkvc(jxa, 2), Utils.mkvc(jya, 2), Utils.mkvc(jza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'J', jxa, jya, jza, jx_num, jy_num, jz_num, tol_MagDipole_Y
            )

        # Plot Tx and Rx locations on mesY
        if plotIt:

            x = self.XYZ_CC[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fy[0], self.src_loc_Fy[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot J
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('J', x, jxa, jya, jza, jx_num, jy_num, jz_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Jx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Jy do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Jz do not agree.')

    def test_3DMesh_Y_MagDipoleTest_H(self):
        print('Testing H components of a Y-oriented analytic harmonic magnetic dipole.')
        # Specify toleraces
        tol_MagDipole_Y = 4e-2

        # Get H which lives on edges
        h_numCC = self.numFields_MagDipole_Y[self.dm_y, 'h']

        # Apply data projection matrix to get J at the reciever locations
        hx_num, hy_num, hz_num = self.Pccx*h_numCC, self.Pccy*h_numCC, self.Pccz*h_numCC

        # Get analytic solution
        hxa, hya, hza = EM.Analytics.FDEMDipolarfields.H_from_MagneticDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        hxa, hya, hza = Utils.mkvc(hxa, 2), Utils.mkvc(hya, 2), Utils.mkvc(hza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'H', hxa, hya, hza, hx_num, hy_num, hz_num, tol_MagDipole_Y
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x = self.XYZ_CC[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fy[0], self.src_loc_Fy[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot H
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('H', x, hxa, hya, hza, hx_num, hy_num, hz_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Hx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Hy do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Hz do not agree.')

    def test_3DMesh_Y_MagDipoleTest_B(self):
        print('Testing B components of a Y-oriented analytic harmonic magnetic dipole.')

        # Specify toleraces
        tol_MagDipole_Y = 4e-2

        # Get E which lives on cell centres
        b_numF = self.numFields_MagDipole_Y[self.dm_y, 'b']

        # Apply data projection matrix to get E at the reciever locations
        bx_num, by_num, bz_num = self.Pfx*b_numF, self.Pfy*b_numF, self.Pfz*b_numF

        # Get analytic solution
        bxa, _ , _  = EM.Analytics.FDEMDipolarfields.B_from_MagneticDipoleWholeSpace(self.XYZ_Fx, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        _ , bya , _ = EM.Analytics.FDEMDipolarfields.B_from_MagneticDipoleWholeSpace(self.XYZ_Fy, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        _ , _ , bza = EM.Analytics.FDEMDipolarfields.B_from_MagneticDipoleWholeSpace(self.XYZ_Fz, self.src_loc_Fy, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Y',kappa= self.kappa)
        bxa, bya, bza = Utils.mkvc(bxa, 2), Utils.mkvc(bya, 2), Utils.mkvc(bza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'B', bxa, bya, bza, bx_num, by_num, bz_num, tol_MagDipole_Y
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x_Bx = self.XYZ_Fx[:, 0]
            x_By = self.XYZ_Fy[:, 0]
            x_Bz = self.XYZ_Fz[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fy[0], self.src_loc_Fy[2], 'ro', ms=8)
            ax.plot(self.XYZ_Fx[:, 0], self.XYZ_Fx[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fy[:, 0], self.XYZ_Fy[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fz[:, 0], self.XYZ_Fz[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot E
            fig, ax = plt.subplots(2, 3, figsize=(20, 10))

            plotLine_num_ana(ax[0], x_Bx, bx_num.real, bxa.real,
                             title='B_x Real')
            plotLine_num_ana(ax[1], x_Bx, bx_num.imag, bxa.imag,
                             title='B_x Imag')

            plotLine_num_ana(ax[2], x_By, by_num.real, bya.real,
                             title='B_y Real')
            plotLine_num_ana(ax[3], x_By, by_num.imag, bya.imag,
                             title='B_y Imag')

            plotLine_num_ana(ax[4], x_Bz, bz_num.real, bza.real,
                             title='B_z Real')
            plotLine_num_ana(ax[5], x_Bz, bz_num.imag, bza.imag,
                             title='B_z Imag')

            plt.legend(['Num', 'Ana'], bbox_to_anchor=(1.5, 0.5))
            plt.tight_layout()
            plt.show()

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Bx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for By do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Bz do not agree.')

class Z_MaDipoleTest_3DMesh(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        print('Testing a Z-oriented analytic harmonic magnetic dipole against the numerical solution on a 3D-tesnsor mesh.')

        # Define model parameters
        self.sigmaback = SIGMABACK
        # mu = mu_0*(1+kappa)
        self.kappa = KAPPA

        # Create 3D mesh
        self.mesh = setUpMesh()

        # Set source parameters
        self.freq = 500.
        src_loc = np.r_[0., 0., -35]
        src_loc_CCInd = Utils.closestPoints(self.mesh, src_loc, 'CC')
        self.src_loc_CC = self.mesh.gridCC[src_loc_CCInd,:]
        self.src_loc_CC = self.src_loc_CC[0]

        # Compute skin depth
        skdpth = 500. / np.sqrt(self.sigmaback * self.freq)

        # make sure mesh is big enough
        # print('skin depth =', skdpth)
        # self.assertTrue(self.mesh.hx.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hy.sum() > skdpth*2.)
        # self.assertTrue(self.mesh.hz.sum() > skdpth*2.)

        # Create wholespace models
        SigmaBack = self.sigmaback*np.ones((self.mesh.nC))
        MuBack = (mu_0*(1 + self.kappa))*np.ones((self.mesh.nC))

        # Define reciever locations
        xlim = 40. # x locations from -50 to 50
        xInd = np.where(np.abs(self.mesh.vectorCCx) < xlim)
        x = self.mesh.vectorCCx[xInd[0]]
        y = 10.
        z = 30.

        # where we choose to measure
        XYZ = Utils.ndgrid(x, np.r_[y], np.r_[z])

        # Cell centred recievers
        XYZ_CCInd = Utils.closestPoints(self.mesh, XYZ, 'CC')
        self.XYZ_CC = self.mesh.gridCC[XYZ_CCInd,:]

        # Edge recievers
        XYZ_ExInd = Utils.closestPoints(self.mesh, XYZ, 'Ex')
        self.XYZ_Ex = self.mesh.gridEx[XYZ_ExInd,:]
        XYZ_EyInd = Utils.closestPoints(self.mesh, XYZ, 'Ey')
        self.XYZ_Ey = self.mesh.gridEy[XYZ_EyInd,:]
        XYZ_EzInd = Utils.closestPoints(self.mesh, XYZ, 'Ez')
        self.XYZ_Ez = self.mesh.gridEz[XYZ_EzInd,:]

        # Face recievers
        XYZ_FxInd = Utils.closestPoints(self.mesh, XYZ, 'Fx')
        self.XYZ_Fx = self.mesh.gridFx[XYZ_FxInd,:]
        XYZ_FyInd = Utils.closestPoints(self.mesh, XYZ, 'Fy')
        self.XYZ_Fy = self.mesh.gridFy[XYZ_FyInd,:]
        XYZ_FzInd = Utils.closestPoints(self.mesh, XYZ, 'Fz')
        self.XYZ_Fz = self.mesh.gridFz[XYZ_FzInd,:]

        # Form data interpolation matrices
        Pcc = self.mesh.getInterpolationMat(self.XYZ_CC, 'CC')
        Zero = sp.csr_matrix(Pcc.shape)
        self.Pccx, self.Pccy, self.Pccz = sp.hstack([Pcc, Zero, Zero]), sp.hstack([Zero, Pcc, Zero]), sp.hstack([Zero, Zero, Pcc])

        self.Pex, self.Pey, self.Pez = self.mesh.getInterpolationMat(self.XYZ_Ex, 'Ex'), self.mesh.getInterpolationMat(self.XYZ_Ey, 'Ey'), self.mesh.getInterpolationMat(self.XYZ_Ez, 'Ez')
        self.Pfx, self.Pfy, self.Pfz = self.mesh.getInterpolationMat(self.XYZ_Fx, 'Fx'), self.mesh.getInterpolationMat(self.XYZ_Fy, 'Fy'), self.mesh.getInterpolationMat(self.XYZ_Fz, 'Fz')

        # Define the source
        # Search over x-faces to find face nearest src_loc
        s_ind = Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fz') + self.mesh.nFx + self.mesh.nFy
        dm = np.zeros(self.mesh.nF, dtype=complex)
        dm[s_ind] = (-1j*(2*np.pi*self.freq)*(mu_0*(1 + self.kappa)))/self.mesh.hz.min()
        self.dm_z = [EM.FDEM.Src.RawVec_m([], self.freq, dm/self.mesh.area)]

        self.src_loc_Fz = self.mesh.gridFz[Utils.closestPoints(self.mesh, self.src_loc_CC, 'Fz'),:]
        self.src_loc_Fz = self.src_loc_Fz[0]

        # Create survey and problem object
        survey = EM.FDEM.Survey(self.dm_z)
        mapping = [('sigma', Maps.IdentityMap(self.mesh)), ('mu', Maps.IdentityMap(self.mesh))]
        problem = EM.FDEM.Problem3D_b(self.mesh, mapping=mapping)

        # Pair problem and survey
        problem.pair(survey)
        problem.Solver = Solver

        # Solve forward problem
        self.numFields_MagDipole_Z = problem.fields(np.r_[SigmaBack, MuBack])

        # setUp_Done = True

    def test_3DMesh_Z_MagDipoleTest_E(self):
        print('Testing E components of a Z-oriented analytic harmonic magnetic dipole.')

        # Specify toleraces
        tol_MagDipole_Z = 2e-2

        # Get E which lives on edges
        e_numE = self.numFields_MagDipole_Z[self.dm_z, 'e']

        # Apply data projection matrix to get E at the reciever locations
        ex_num, ey_num, ez_num = self.Pex*e_numE, self.Pey*e_numE, self.Pez*e_numE

        # Get analytic solution
        exa, _ , _  = EM.Analytics.FDEMDipolarfields.E_from_MagneticDipoleWholeSpace(self.XYZ_Ex, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        _ , eya , _ = EM.Analytics.FDEMDipolarfields.E_from_MagneticDipoleWholeSpace(self.XYZ_Ey, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        _ , _ , eza = EM.Analytics.FDEMDipolarfields.E_from_MagneticDipoleWholeSpace(self.XYZ_Ez, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        exa, eya, eza = Utils.mkvc(exa, 2), Utils.mkvc(eya, 2), Utils.mkvc(eza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'E', exa, eya, eza, ex_num, ey_num, ez_num, tol_MagDipole_Z
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x_Ex = self.XYZ_Ex[:, 0]
            x_Ey = self.XYZ_Ey[:, 0]
            x_Ez = self.XYZ_Ez[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fz[0], self.src_loc_Fz[2], 'ro', ms=8)
            ax.plot(self.XYZ_Ex[:, 0], self.XYZ_Ex[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ey[:, 0], self.XYZ_Ey[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Ez[:, 0], self.XYZ_Ez[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot E
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('E', x, exa, eya, eza, ex_num, ey_num, ez_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Ex do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Ey do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Ez do not agree.')

    def test_3DMesh_Z_MagDipoleTest_J(self):
        print('Testing J components of a Z-oriented analytic harmonic magnetic dipole.')
        # Specify toleraces
        tol_MagDipole_Z = 2e-2

        # Get J which lives on faces
        j_numCC = self.numFields_MagDipole_Z[self.dm_z, 'j']

        # Apply data projection matrix to get J at the reciever locations
        jx_num, jy_num, jz_num = self.Pccx*j_numCC, self.Pccy*j_numCC, self.Pccz*j_numCC

        # Get analytic solution
        jxa, jya, jza = EM.Analytics.FDEMDipolarfields.J_from_MagneticDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        jxa, jya, jza = Utils.mkvc(jxa, 2), Utils.mkvc(jya, 2), Utils.mkvc(jza, 2)

        print str('Comp').center(4), str('Ana').center(25)              , str('Num').center(25)                 , str('Num - Ana').center(25)               , str('(Num - Ana)/Ana').center(25)                             , str('Pass Status').center(12)
        print str('J_x:').rjust(4) , repr(np.linalg.norm(jxa)).rjust(25), repr(np.linalg.norm(jx_num)).rjust(25), repr(np.linalg.norm(jxa-jx_num)).rjust(25), repr(np.linalg.norm(jxa-jx_num)/np.linalg.norm(jxa)).rjust(25), repr(np.linalg.norm(jxa-jx_num)/np.linalg.norm(jxa) < tol_MagDipole_Z).center(12)
        print str('J_y:').rjust(4) , repr(np.linalg.norm(jya)).rjust(25), repr(np.linalg.norm(jy_num)).rjust(25), repr(np.linalg.norm(jya-jy_num)).rjust(25), repr(np.linalg.norm(jya-jy_num)/np.linalg.norm(jya)).rjust(25), repr(np.linalg.norm(jya-jy_num)/np.linalg.norm(jya) < tol_MagDipole_Z).center(12)
        print str('J_z:').rjust(4) , repr(np.linalg.norm(jza)).rjust(25), repr(np.linalg.norm(jz_num)).rjust(25), repr(np.linalg.norm(jza-jz_num)).rjust(25), str('').rjust(25)                                             , repr(np.linalg.norm(jza-jz_num) < tol_NumErrZero).center(12)
        print
        self.assertTrue(np.linalg.norm(jxa-jx_num)/np.linalg.norm(jxa) < tol_MagDipole_Z, msg='Analytic and numeric solutions for Jx do not agree.')
        self.assertTrue(np.linalg.norm(jya-jy_num)/np.linalg.norm(jya) < tol_MagDipole_Z, msg='Analytic and numeric solutions for Jy do not agree.')
        self.assertTrue(np.linalg.norm(jza-jz_num) < tol_NumErrZero, msg='Analytic and numeric solutions for Jz do not agree.')

        # Plot Tx and Rx locations on mesY
        if plotIt:

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fz[0], self.src_loc_Fz[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot J
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('J', x, jxa, jya, jza, jx_num, jy_num, jz_num)

    def test_3DMesh_Z_MagDipoleTest_H(self):
        print('Testing H components of a Z-oriented analytic harmonic magnetic dipole.')
        # Specify toleraces
        tol_MagDipole_Z = 2e-2

        # Get H which lives on edges
        h_numCC = self.numFields_MagDipole_Z[self.dm_z, 'h']

        # Apply data projection matrix to get J at the reciever locations
        hx_num, hy_num, hz_num = self.Pccx*h_numCC, self.Pccy*h_numCC, self.Pccz*h_numCC

        # Get analytic solution
        hxa, hya, hza = EM.Analytics.FDEMDipolarfields.H_from_MagneticDipoleWholeSpace(self.XYZ_CC, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        hxa, hya, hza = Utils.mkvc(hxa, 2), Utils.mkvc(hya, 2), Utils.mkvc(hza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'H', hxa, hya, hza, hx_num, hy_num, hz_num, tol_MagDipole_Z
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x = self.XYZ_CC[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fz[0], self.src_loc_Fz[2], 'ro', ms=8)
            ax.plot(self.XYZ_CC[:, 0], self.XYZ_CC[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot H
            x = self.XYZ_CC[:, 0]
            plotFields_num_ana('H', x, hxa, hya, hza, hx_num, hy_num, hz_num)

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Hx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for Hy do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Hz do not agree.')

    def test_3DMesh_Z_MagDipoleTest_B(self):
        print('Testing B components of a Z-oriented analytic harmonic magnetic dipole.')

        # Specify toleraces
        tol_MagDipole_Z = 2e-2

        # Get E which lives on cell centres
        b_numF = self.numFields_MagDipole_Z[self.dm_z, 'b']

        # Apply data projection matrix to get E at the reciever locations
        bx_num, by_num, bz_num = self.Pfx*b_numF, self.Pfy*b_numF, self.Pfz*b_numF

        # Get analytic solution
        bxa, _ , _  = EM.Analytics.FDEMDipolarfields.B_from_MagneticDipoleWholeSpace(self.XYZ_Fx, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        _ , bya , _ = EM.Analytics.FDEMDipolarfields.B_from_MagneticDipoleWholeSpace(self.XYZ_Fy, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        _ , _ , bza = EM.Analytics.FDEMDipolarfields.B_from_MagneticDipoleWholeSpace(self.XYZ_Fz, self.src_loc_Fz, self.sigmaback, Utils.mkvc(np.array(self.freq)),orientation='Z',kappa= self.kappa)
        bxa, bya, bza = Utils.mkvc(bxa, 2), Utils.mkvc(bya, 2), Utils.mkvc(bza, 2)

        passed_x, passed_y, passed_z = errorLog(
            'B', bxa, bya, bza, bx_num, by_num, bz_num, tol_MagDipole_Z
            )

        # Plot Tx and Rx locations on mesh
        if plotIt:

            x_Bx = self.XYZ_Fx[:, 0]
            x_By = self.XYZ_Fy[:, 0]
            x_Bz = self.XYZ_Fz[:, 0]

            # Plot Tx and Rx locations on mesh
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            ax.plot(self.src_loc_Fz[0], self.src_loc_Fz[2], 'ro', ms=8)
            ax.plot(self.XYZ_Fx[:, 0], self.XYZ_Fx[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fy[:, 0], self.XYZ_Fy[:, 2], 'k.', ms=6)
            ax.plot(self.XYZ_Fz[:, 0], self.XYZ_Fz[:, 2], 'k.', ms=6)
            self.mesh.plotSlice(np.zeros(self.mesh.nC)*np.nan, grid=True, normal="Y", ax = ax)

            # Plot Br
            fig, ax = plt.subplots(2, 3, figsize=(20, 10))

            plotLine_num_ana(ax[0], x_Bx, bx_num.real, bxa.real,
                             title='B_x Real')
            plotLine_num_ana(ax[1], x_Bx, bx_num.imag, bxa.imag,
                             title='B_x Imag')

            plotLine_num_ana(ax[2], x_By, by_num.real, bya.real,
                             title='B_y Real')
            plotLine_num_ana(ax[3], x_By, by_num.imag, bya.imag,
                             title='B_y Imag')

            plotLine_num_ana(ax[4], x_Bz, bz_num.real, bza.real,
                             title='B_z Real')
            plotLine_num_ana(ax[5], x_Bz, bz_num.imag, bza.imag,
                             title='B_z Imag')

            plt.legend(['Num', 'Ana'], bbox_to_anchor=(1.5, 0.5))
            plt.tight_layout()
            plt.show()

        self.assertTrue(passed_x, msg='Analytic and numeric solutions for Bx do not agree.')
        self.assertTrue(passed_y, msg='Analytic and numeric solutions for By do not agree.')
        self.assertTrue(passed_z, msg='Analytic and numeric solutions for Bz do not agree.')



if __name__ == '__main__':
    unittest.main()