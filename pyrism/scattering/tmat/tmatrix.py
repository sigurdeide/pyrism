from __future__ import division

import sys
import warnings

import numpy as np
from pyrism.core.tma import (NMAX_VEC_WRAPPER, SZ_S_VEC_WRAPPER, SZ_AF_VEC_WRAPPER, DBLQUAD_Z_S_WRAPPER,
                             XSEC_QS_S_WRAPPER, XSEC_ASY_S_WRAPPER, XSEC_ASY_AF_WRAPPER, XSEC_QE_WRAPPER,
                             XSEC_QSI_WRAPPER, KE_WRAPPER, KS_WRAPPER, KA_WRAPPER, KT_WRAPPER,
                             equal_volume_from_maximum_wrapper)
from respy import Angles, EMW, align_all

from pyrism.scattering.tmat.orientation import Orientation
from pyrism.scattering.tmat.tm_auxiliary import param_radius_type, param_shape, param_orientation

# python 3.6 comparability
if sys.version_info < (3, 0):
    srange = xrange
else:
    srange = range

warnings.simplefilter('default')

PI = 3.14159265359
RAD_TO_DEG = 180.0 / PI
DEG_TO_RAD = PI / 180.0


class TMatrix(Angles, object):
    def __init__(self, iza, vza, iaa, vaa, frequency, radius, eps, alpha=0.0, beta=0.0, N=1,
                 radius_type='REV', shape='SPH', orientation='S', axis_ratio=1.0, orientation_pdf=None, n_alpha=5,
                 n_beta=10, normalize=False, nbar=0.0, angle_unit='DEG', frequency_unit='GHz', radius_unit='m',
                 verbose=False):

        """T-Matrix scattering from nonspherical particles.

        Class for simulating scattering from nonspherical particles with the
        T-Matrix method. Uses a wrapper to the Fortran code by M. Mishchenko.

        Parameters
        ----------
        iza, vza, iaa, vaa : int, float or array_like
            Incidence (iza) and scattering (vza) zenith angle and incidence and viewing
            azimuth angle (ira, vra) in [DEG] or [RAD] (see parameter angle_unit).
        frequency : int float or array_like
            The frequency of incident EM Wave in {'Hz', 'MHz', 'GHz', 'THz'} (see parameter frequency_unit).
        radius : int float or array_like
            Equivalent particle radius in [cm].
        eps : complex
            The complex refractive index.
        alpha, beta: int, float or array_like
            The Euler angles of the particle orientation in [DEG] or [RAD] (see parameter angle_unit). Default is 0.0.
        radius_type : {'EV', 'M', 'REA'}
            Specification of particle radius:
                * 'REV': radius is the equivalent volume radius (default).
                * 'M': radius is the maximum radius.
                * 'REA': radius is the equivalent area radius.
        shape : {'SPH', 'CYL'}
            Shape of the particle:
                * 'SPH' : spheroid,
                * 'CYL' : cylinders.
        orientation : {'S', 'AA', 'AF'}
            The function to use to compute the orientational scattering properties:
                * 'S': Single (default).
                * 'AA': Averaged Adaptive
                * 'AF': Averaged Fixed.
        orientation_pdf: {'gauss', 'uniform'}, callable
            Particle orientation Probability Density Function (PDF) for orientational averaging:
                * 'gauss': Use a Gaussian PDF (default).
                * 'uniform': Use a uniform PDR.
        axis_ratio : int or float
            The horizontal-to-rotational axis ratio.
        n_alpha : int
            Number of integration points in the alpha Euler angle. Default is 5.
        n_beta : int
            Umber of integration points in the beta Euler angle. Default is 10.
        num_points : int
            The number of points for which to sample the PSD and
            scattering properties for; default num_points=1024 should be good
            for most purposes.
        normalize : boolean, optional
            Set to 'True' to make kernels 0 at nadir view illumination. Since all implemented kernels are normalized
            the default value is False.
        nbar : float, optional
            The sun or incidence zenith angle at which the isotropic term is set
            to if normalize is True. The default value is 0.0.
        angle_unit : {'DEG', 'RAD'}, optional
            * 'DEG': All input angles (iza, vza, raa) are in [DEG] (default).
            * 'RAD': All input angles (iza, vza, raa) are in [RAD].
        frequency_unit : {'Hz', 'MHz', 'GHz', 'THz'}
            Unit of entered frequency. Default is 'GHz'.
        radius_unit : {'m', 'cm', 'nm'}
            Unit of the radius in meter (m), centimeter (cm) or nanometer (nm).

        Returns
        -------
        TMatrix.S : array_like
            Complex Scattering Matrix.
        TMatrix.Z : array_like
            Phase Matrix.
        TMatrix.SZ : list or array_like
             Complex Scattering Matrix and Phase Matrix.

        TMatrix.ks : list or array_like
            Scattering coefficient matrix in [1/cm] for VV and HH polarization.
        TMatrix.ka : list or array_like
            Absorption coefficient matrix in [1/cm] for VV and HH polarization.
        TMatrix.ke : list or array_like
            Extinction coefficient matrix in [1/cm] for VV and HH polarization.
        TMatrix.kt : list or array_like
            Transmittance coefficient matrix in [1/cm] for VV and HH polarization.
        TMatrix.omega : list or array_like
            Single scattering albedo coefficient matrix in [1/cm] for VV and HH polarization.

        TMatrix.QS : list or array_like
            Scattering Cross Section in [cm^2] for VV and HH polarization.
        TMatrix.QE : list or array_like
            Extinction Cross Section in [cm^2] for VV and HH polarization.
        TMatrix.QAS : list or array_like
            Asymetry Factor in [cm^2] for VV and HH polarization.
        TMatrix.I : list or array_like
            Scattering intensity for VV and HH polarization.

        TMatrix.compute_SZ(...) :
            Function to recalculate SZ for different angles.

        See Also
        --------
        radarpy.Angles
        pyrism.Orientation

        """
        # Check input parameter ----------------------------------------------------------------------------------------
        if radius_type not in param_radius_type.keys():
            raise ValueError("Radius type must be {0}".format(param_radius_type.keys()))

        if shape not in param_shape.keys():
            raise ValueError("Shape must be {0}".format(param_shape.keys()))

        if orientation not in param_orientation:
            raise ValueError("Orientation must be {0}".format(param_orientation))

        # Define angles and align data ---------------------------------------------------------------------------------
        input_data = (iza, vza, iaa, vaa, frequency, radius, axis_ratio, alpha, beta, eps.real, eps.imag, N)

        (iza, vza, iaa, vaa, frequency, radius, axis_ratio, alpha, beta, eps_real,
         eps_imag, N) = align_all(input_data, dtype=np.double)

        Angles.__init__(self, iza=iza, vza=vza, raa=None, iaa=iaa, vaa=vaa, alpha=alpha, beta=beta,
                        normalize=normalize, angle_unit=angle_unit, nbar=nbar)

        if normalize:
            data = (frequency, radius, axis_ratio, alpha, beta, eps.real, eps.imag)
            frequency, radius, axis_ratio, alpha, beta, eps_real, eps_imag = self.align_with(data)

        # Define Frequency ---------------------------------------------------------------------------------------------
        self.EMW = EMW(input=frequency, unit=frequency_unit, output=radius_unit)

        self.frequency_unit = self.EMW.frequency_unit
        self.wavelength_unit = self.EMW.wavelength_unit
        self.radius_unit = self.EMW.wavelength_unit

        self.__wavelength = self.EMW.wavelength
        self.__frequency_unit = self.EMW.frequency_unit
        self.__wavelength_unit = self.EMW.wavelength_unit
        self.__radius_unit = self.EMW.wavelength_unit
        self.__frequency = self.EMW.frequency
        self.__k0 = self.EMW.k0

        # Self Definitions ---------------------------------------------------------------------------------------------
        self.verbose = verbose
        self.__radius = radius
        self.__radius_type = param_radius_type[radius_type]

        self.__axis_ratio = axis_ratio
        self.__shape_volume = param_shape[shape]

        self.ddelt = 1e-3
        self.ndgs = 2

        self.__orient = orientation
        self.__or_pdf = self.__get_pdf(orientation_pdf)

        self.__n_alpha = int(n_alpha)
        self.__n_beta = int(n_beta)

        self.__epsi = eps_imag
        self.__epsr = eps_real

        self.__N = N
        self.__chi = self.__k0 * self.__radius

        self.__S = None
        self.__Z = None
        self.__Snorm = None
        self.__Znorm = None
        self.__dblZi = None
        self.__XS = None
        self.__XAS = None
        self.__XE = None
        self.__XI = None
        self.__ke = None
        self.__ks = None
        self.__ka = None
        self.__omega = None
        self.__kt = None

        # Calculations -------------------------------------------------------------------------------------------------
        self.__nmax = self.__NMAX()

    # ------------------------------------------------------------------------------------------------------------------
    # Magic Methods
    # ------------------------------------------------------------------------------------------------------------------
    def __str__(self):
        vals = dict()

        vals['nmax'] = self.nmax.base.mean()
        vals['radius'] = self.radius.mean()
        vals['radius_unit'] = self.radius_unit
        vals['frequency_unit'] = self.EMW.frequency_unit
        vals['wavelength_unit'] = self.EMW.wavelength_unit
        vals['frequency'] = self.EMW.frequency
        vals['wavelength'] = self.EMW.wavelength
        vals['ratio'] = self.axis_ratio.mean()

        if self.normalize is False:
            vals['izaDeg'] = self.izaDeg.mean()
            vals['vzaDeg'] = self.vzaDeg.mean()
            vals['raaDeg'] = self.raaDeg.mean()
            vals['iaaDeg'] = self.iaaDeg.mean()
            vals['vaaDeg'] = self.vaaDeg.mean()
            vals['alphaDeg'] = self.alphaDeg.mean()
            vals['betaDeg'] = self.betaDeg.mean()

        else:
            vals['izaDeg'] = self.izaDeg[0:-1].mean()
            vals['vzaDeg'] = self.vzaDeg[0:-1].mean()
            vals['raaDeg'] = self.raaDeg[0:-1].mean()
            vals['iaaDeg'] = self.iaaDeg[0:-1].mean()
            vals['vaaDeg'] = self.vaaDeg[0:-1].mean()
            vals['alphaDeg'] = self.alphaDeg[0:-1].mean()
            vals['betaDeg'] = self.betaDeg[0:-1].mean()

        info = 'Class                                                      : TMatrix\n' \
               'Mean incidence and viewing zenith angle [DEG]              : {izaDeg}, {vzaDeg}\n' \
               'Mean relative, incidence and viewing azimuth angle [DEG]   : {raaDeg}, {iaaDeg}, {vaaDeg}\n' \
               'Mean alpha andbeta angle [DEG]                             : {alphaDeg}, {betaDeg}\n' \
               'Mean NMAX                                                  : {nmax}\n' \
               'Mean radius                                                : {radius} {radius_unit}\n' \
               'Mean ratio                                                 : {ratio}\n' \
               'Mean frequency                                             : {frequency} {frequency_unit}\n' \
               'Mean wavelength                                            : {wavelength} {wavelength_unit}'.format(
            **vals)

        return info

    def __len__(self):
        return len(self.nmax)

    # ------------------------------------------------------------------------------------------------------------------
    # Property Calls with Setters
    # ------------------------------------------------------------------------------------------------------------------
    @property
    def nmax(self):
        return self.__nmax

    @property
    def frequency(self):
        return self.EMW.frequency

    @frequency.setter
    def frequency(self, value):
        value = np.asarray(value, dtype=np.double).flatten()

        if len(value) < self.len:
            warnings.warn("The length of the input is shorter than the other parameters. The input is therefore "
                          "adjusted to the other parameters. ")

        data = (value, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi)
        value, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi = self.align_with(data)

        self.EMW.frequency = value
        self.__wavelength = self.EMW.wavelength
        self.__frequency = self.EMW.frequency
        self.__k0 = self.EMW.k0

        self.__update_attributes()

    @property
    def wavelength(self):
        return self.EMW.wavelength

    @wavelength.setter
    def wavelength(self, value):
        value = np.asarray(value, dtype=np.double).flatten()

        if len(value) < self.len:
            warnings.warn("The length of the input is shorter than the other parameters. The input is therefore "
                          "adjusted to the other parameters. ")

        data = (value, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi)
        value, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi = self.align_with(data)

        self.EMW.wavelength = value
        self.__wavelength = self.EMW.wavelength
        self.__frequency = self.EMW.frequency
        self.__k0 = self.EMW.k0

        data = (self.__radius, self.__axis_ratio, self.__epsr, self.__epsi)
        self.__radius, self.__axis_ratio, self.__epsr, self.__epsi = self.align_with(data)

        self.__update_attributes()

    @property
    def k0(self):
        return self.__k0

    @property
    def radius(self):
        return self.__radius

    @radius.setter
    def radius(self, value):
        value = np.asarray(value, dtype=np.double).flatten()

        if len(value) < self.len:
            warnings.warn("The length of the input is shorter than the other parameters. The input is therefore "
                          "adjusted to the other parameters. ")

        data = (value, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi)
        value, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi = self.align_with(data)

        value = self.EMW.align_with(value)
        self.__wavelength = self.EMW.wavelength
        self.__frequency = self.EMW.frequency
        self.__k0 = self.EMW.k0

        self.__radius = value

        self.__update_attributes()

    @property
    def radius_type(self):
        return self.__radius_type

    @radius_type.setter
    def radius_type(self, value):
        if value not in param_radius_type.keys():
            raise ValueError("Radius type must be {0}".format(param_radius_type.keys()))

        self.__radius_type = param_radius_type[value]

        self.__update_attributes()

    @property
    def axis_ratio(self):
        return self.__axis_ratio

    @axis_ratio.setter
    def axis_ratio(self, value):
        value = np.asarray(value, dtype=np.double).flatten()

        if len(value) < self.len:
            warnings.warn("The length of the input is shorter than the other parameters. The input is therefore "
                          "adjusted to the other parameters. ")

        data = (value, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi)
        value, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi = self.align_with(data)

        value = self.EMW.align_with(value)
        self.__wavelength = self.EMW.wavelength
        self.__frequency = self.EMW.frequency
        self.__k0 = self.EMW.k0

        self.__axis_ratio = value

        self.__update_attributes()

    @property
    def shape_volume(self):
        return self.__shape_volume

    @shape_volume.setter
    def shape_volume(self, value):
        if value not in param_shape.keys():
            raise ValueError("Shape must be {0}".format(param_shape.keys()))

        self.__shape_volume = param_shape[value]
        self.__update_attributes()

    @property
    def eps(self):
        return self.__epsr + self.__epsi * 1j

    @eps.setter
    def eps(self, value):
        epsr = value.real
        epsi = value.imag

        epsr = np.asarray(epsr, dtype=np.double).flatten()
        epsi = np.asarray(epsi, dtype=np.double).flatten()

        if len(epsr) < self.len:
            warnings.warn("The length of the input is shorter than the other parameters. The input is therefore "
                          "adjusted to the other parameters. ")

        data = (epsr, epsi, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi)
        epsr, epsi, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi = self.align_with(data)

        epsr, epsi = self.EMW.align_with((epsr, epsi))
        self.__wavelength = self.EMW.wavelength
        self.__frequency = self.EMW.frequency
        self.__k0 = self.EMW.k0

        self.__epsr, self.__epsi = epsr, epsi

        self.__update_attributes()

    @property
    def orientation(self):
        return self.__orient

    @orientation.setter
    def orientation(self, value):
        if value not in param_orientation:
            raise ValueError("Orientation must be {0}".format(param_orientation))

        self.__orient = value

        self.__update_attributes()

    @property
    def orientation_pdf(self):
        return self.__or_pdf

    @orientation_pdf.setter
    def orientation_pdf(self, value):
        self.__or_pdf = self.__get_pdf(value)

        self.__update_attributes()

    @property
    def n_alpha(self):
        return self.__n_alpha

    @n_alpha.setter
    def n_alpha(self, value):
        self.__n_alpha = int(value)

        self.__update_attributes()

    @property
    def n_beta(self):
        return self.__n_beta

    @n_beta.setter
    def n_beta(self, value):
        self.__n_beta = int(value)

        self.__update_attributes()

    @property
    def N(self):
        return self.__N

    # @N.setter
    # def N(self, value):
    #     value = np.asarray(value, dtype=np.int).flatten()
    #
    #     if len(value) < self.len:
    #         warnings.warn("The length of the input is shorter than the other parameters. The input is therefore "
    #                       "adjusted to the other parameters. ")
    #
    #     data = (value, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi)
    #     value, self.__radius, self.__axis_ratio, self.__epsr, self.__epsi = self.align_with(data)
    #
    #     value = self.EMW.align_with(value)
    #     self.__wavelength = self.EMW.wavelength
    #     self.__frequency = self.EMW.frequency
    #     self.__k0 = self.EMW.k0
    #
    #     self.__N = value
    #
    #     self.__update_attributes()

    # ------------------------------------------------------------------------------------------------------------------
    # Property Calls
    # ------------------------------------------------------------------------------------------------------------------
    # Access to Array Specific Attributes ------------------------------------------------------------------------------
    @property
    def len(self):
        """
        Length of array

        Returns
        -------
        len : int
        """
        return self.__nmax.shape[0]

    @property
    def shape(self):
        """
        Shape of array

        Returns
        -------
        shape : tuple
        """
        return self.S.shape

    # Auxiliary Properties- --------------------------------------------------------------------------------------------
    @property
    def chi(self):
        return self.k0 * self.radius

    @property
    def factor(self):
        return (2 * PI * self.__N * 1j) / self.k0

    # Scattering and Phase Matrices ------------------------------------------------------------------------------------
    @property
    def S(self):
        """
        Scattering matrix.

        Returns
        -------
        S : array_like
        """
        if self.__S is None:
            self.__S, self.__Z = self.compute_SZ()

        return self.__property_return(self.__S, normalize=False)

    @property
    def Z(self):
        """
        Phase matrix.

        Returns
        -------
        Z : array_like
        """
        if self.__Z is None:
            self.__S, self.__Z = self.compute_SZ()

        return self.__property_return(self.__Z)

    @property
    def SZ(self):
        """
        Scattering and phase matrix.

        Returns
        -------
        S, Z : tuple
        """
        if self.__S is None:
            self.__S, self.__Z = self.compute_SZ()

        elif self.__Z is None:
            self.__S, self.__Z = self.compute_SZ()

        return self.__property_return(self.__S, normalize=False), self.__property_return(self.__Z)

    @property
    def Znorm(self):
        """
        Normalization matrices of the phase matrix.
        Normalization adds an extra column with S and Z values for iza = nbar and vza = 0.

        Returns
        -------
        Z : list or array_like
        """
        if self.normalize:
            if self.__Z is None:
                self.__S, self.__Z = self.compute_SZ()

            if self.__Znorm is None:
                self.__Znorm = np.zeros((4, 4))

                for i in range(4):
                    for j in range(4):
                        self.__Znorm[i, j] = self.__Z[-1, i, j]

            return self.__Znorm

        else:
            return None

    @property
    def Snorm(self):
        """
        Normalization matrices of the scattering matrix.
        Normalization adds an extra column with S and Z values for iza = nbar and vza = 0.

        Returns
        -------
        S, Z : list or array_like
        """
        if self.normalize:
            if self.__S is None:
                self.__S, self.__Z = self.compute_SZ()

            if self.__Snorm is None:
                self.__Snorm = np.zeros((4, 4))

                for i in range(4):
                    for j in range(4):
                        self.__Snorm[i, j] = self.__S[-1, i, j]

            return self.__Snorm

        else:
            return None

    # Integration of S and Z -------------------------------------------------------------------------------------------
    @property
    def dblquad(self):
        """
        Half space integration of the phase matrix in incidence direction.

        Returns
        -------
        dbl : list or array_like
        """
        if self.__dblZi is None:
            self.__dblZi = self.__dblquad()

        return self.__property_return(self.__dblZi)

    # Extinction and Scattering Matrices -------------------------------------------------------------------------------
    @property
    def ke(self):
        """
        Extinction matrix for the current setup, with polarization.

        Returns
        -------
        ke : MemoryView, double[:,:}
            MemoryView of type array([[VV, HH]])
        """
        if self.__ke is None:
            self.__ke = self.__KE()

        return self.__property_return(self.__ke, normalize=False)

    @property
    def ks(self):
        """
        Scattering matrix for the current setup, with polarization.

        Returns
        -------
        ks : MemoryView, double[:,:}
            MemoryView of type array([[VV, HH]])
        """
        if self.__ks is None:
            self.__ks = self.__KS()

        return self.__property_return(self.__ks, normalize=False)

    @property
    def ka(self):
        """
        Absorption matrix for the current setup, with polarization.

        Returns
        -------
        ka : MemoryView, double[:,:}
            MemoryView of type array([[VV, HH]])
        """
        if self.__ka is None:
            self.__ka = self.__KA()

        return self.__property_return(self.__ka, normalize=False)

    @property
    def omega(self):
        """
        Single scattering albedo matrix for the current setup, with polarization.

        Returns
        -------
        omega : MemoryView, double[:,:}
            MemoryView of type array([[VV, HH]])
        """
        if self.__omega is None:
            self.__omega = self.__OMEGA()

        return self.__property_return(self.__omega, normalize=False)

    @property
    def kt(self):
        """
        Transmission matrix for the current setup, with polarization.

        Returns
        -------
        kt : MemoryView, double[:,:}
            MemoryView of type array([[VV, HH]])
        """
        if self.__kt is None:
            self.__kt = self.__KT()

        return self.__property_return(self.__kt, normalize=False)

    # Cross Section ----------------------------------------------------------------------------------------------------
    @property
    def QS(self):
        """
        Scattering cross section for the current setup, with polarization.

        Returns
        -------
        QS : array_like
        """

        if self.__XS is None:
            self.__XS = self.__QS()

        return self.__property_return(self.__XS, normalize=False)

    @property
    def QAS(self):
        """
        Asymmetry cross section for the current setup, with polarization.

        Returns
        -------
        QAS : array_like
        """
        if self.__XS is None:
            self.__XS = self.__QS()

        if self.__XAS is None:
            self.__XAS = self.__QAS()

        return self.__property_return(self.__XAS.base / self.__XS.base, normalize=False)

    @property
    def QE(self):
        """
        Extinction cross section for the current setup, with polarization.

        Returns
        -------
        QE : array_like
        """

        if self.__XE is None:
            self.__XE = self.__QE()

        return self.__property_return(self.__XE, normalize=False)

    @property
    def I(self):
        """
        Extinction cross section for the current setup, with polarization.

        Returns
        -------
        QE : array_like
        """

        if self.__XI is None:
            self.__XI = self.__I()

        return self.__property_return(self.__XI, normalize=False)

    # -----------------------------------------------------------------------------------------------------------------
    # User callable methods
    # -----------------------------------------------------------------------------------------------------------------
    def compute_SZ(self, izaDeg=None, vzaDeg=None, iaaDeg=None, vaaDeg=None, alphaDeg=None, betaDeg=None):
        """T-Matrix scattering from single nonspherical particles.

        Class for simulating scattering from nonspherical particles with the
        T-Matrix method. Uses a wrapper to the Fortran code by M. Mishchenko.

        Parameters
        ----------
        izaDeg, vzaDeg, iaaDeg, vaaDeg : None, int, float or array_like
            Incidence (iza) and scattering (vza) zenith angle and incidence and viewing
            azimuth angle (ira, vra) in [DEG].
        alpha, beta: None, int, float or array_like
            The Euler angles of the particle orientation in [DEG].

        Returns
        -------
        S, Z : array_like
            Three dimensional scattering (S) and phase (Z) matrix.

        Note
        ----
        If xzaDeg, xaaDeg, alpha pr beta is None, the inputed angles in __init__ will be choose.

        !!! IMPORTANT !!!
        If the angles are NOT NONE, the new values will NOT be affect the property calls S, Z and SZ!

        """
        if izaDeg is not None:
            _, izaDeg = align_all((self.izaDeg, izaDeg), dtype=np.double)
        else:
            izaDeg = self.izaDeg

        if vzaDeg is not None:
            _, vzaDeg = align_all((self.vzaDeg, vzaDeg), dtype=np.double)
        else:
            vzaDeg = self.vzaDeg

        if iaaDeg is not None:
            _, iaaDeg = align_all((self.iaaDeg, iaaDeg), dtype=np.double)
        else:
            iaaDeg = self.iaaDeg

        if vaaDeg is not None:
            _, vaaDeg = align_all((self.vaaDeg, vaaDeg), dtype=np.double)
        else:
            vaaDeg = self.vaaDeg

        if alphaDeg is not None:
            _, alphaDeg = align_all((self.alphaDeg, alphaDeg), dtype=np.double)
        else:
            alphaDeg = self.alphaDeg

        if betaDeg is not None:
            _, betaDeg = align_all((self.betaDeg, betaDeg), dtype=np.double)
        else:
            betaDeg = self.betaDeg

        if self.__orient is 'S':
            S, Z = SZ_S_VEC_WRAPPER(self.nmax, self.wavelength, izaDeg, vzaDeg, iaaDeg, vaaDeg, alphaDeg, betaDeg)
        elif self.__orient is 'AF':
            S, Z = SZ_AF_VEC_WRAPPER(self.nmax, self.wavelength, izaDeg, vzaDeg, iaaDeg, vaaDeg, self.n_alpha,
                                     self.n_beta, self.or_pdf)
        else:
            raise ValueError("Orientation must be S or AF.")

        return S, Z

    # ------------------------------------------------------------------------------------------------------------------
    #  Auxiliary functions and private methods
    # ------------------------------------------------------------------------------------------------------------------
    def __update_attributes(self):

        self.__nmax = self.__NMAX()
        # Update first S and Z. Because almost all the other parameters are depending on this both matrices.
        if self.__S is not None or self.__Z is not None:
            self.__S, self.__Z = self.compute_SZ()

        if self.__Snorm is not None:
            self.__Snorm = self.Snorm

        if self.__Znorm is not None:
            self.__Znorm = self.Znorm

        if self.__dblZi is not None:
            self.__dblZi = self.__dblquad()

        if self.__XS is not None:
            self.__XS = self.__QS()

        if self.__XAS is not None:
            self.__XAS = self.__QAS()

        if self.__XE is not None:
            self.__XE = self.__QE()

        if self.__XI is not None:
            self.__XI = self.__I()

        if self.__ke is not None:
            self.__ke = self.__KE()

        if self.__kt is not None:
            self.__kt = self.__KT()

        if self.__omega is not None:
            self.__omega = self.__OMEGA()

        if self.__ks is not None:
            self.__ks = self.__KS()

        if self.__ka is not None:
            self.__ka = self.__KA()

    # NMAX, S and Z ----------------------------------------------------------------------------------------------------
    # ---- NMAX ----
    def __NMAX(self):
        """
        Calculate NMAX parameter.
        """
        if self.__radius_type == 2:
            # Maximum radius is not directly supported in the original
            # so we convert it to equal volume radius
            radius_type = 1
            radius = np.zeros_like(self.iza)

            for i, item in enumerate(self.__radius):
                radius[i] = equal_volume_from_maximum_wrapper(item, self.__axis_ratio[i], self.__shape_volume)

        else:
            radius_type = self.__radius_type
            radius = self.__radius

        nmax = NMAX_VEC_WRAPPER(radius=radius, radius_type=radius_type, wavelength=self.__wavelength,
                                eps_real=self.__epsr, eps_imag=self.__epsi,
                                axis_ratio=self.__axis_ratio, shape=self.__shape_volume, verbose=self.verbose)

        self.__radius = radius

        return nmax

    # Integration of Phase and Scattering Matrix -----------------------------------------------------------------------
    def __dblquad(self, iza_flag=True):

        if iza_flag:
            xzaDeg = self.vzaDeg
            xaaDeg = self.vaaDeg
        else:
            xzaDeg = self.izaDeg
            xaaDeg = self.iaaDeg

        if self.__orient is 'S':
            Z = DBLQUAD_Z_S_WRAPPER(self.nmax, self.wavelength, xzaDeg, xaaDeg, self.alphaDeg, self.betaDeg, iza_flag)
        elif self.__orient is 'AF':
            Z = DBLQUAD_Z_S_WRAPPER(self.nmax, self.wavelength, xzaDeg, xaaDeg, self.n_alpha, self.n_beta, self.or_pdf,
                                    iza_flag)
        else:
            raise ValueError("Orientation must be S or AF.")

        return Z.base.reshape((self.len, 4, 4))

    # Cross Section ----------------------------------------------------------------------------------------------------
    def __KE(self):
        S = self.S
        return KE_WRAPPER(self.factor, S)

    def __KT(self):
        ke = self.ke

        return KT_WRAPPER(ke)

    def __OMEGA(self):
        QS = self.QS
        QE = self.QE

        return QS.base / QE.base

    def __KS(self):

        ke = self.ke
        omega = self.omega

        return KS_WRAPPER(ke, omega)

    def __KA(self):
        ks = self.ks
        omega = self.omega

        return KA_WRAPPER(ks, omega)

    def __QS(self):
        """
        Scattering cross section for the current setup, with polarization.
        """

        if self.__orient is 'S':
            QS = XSEC_QS_S_WRAPPER(self.nmax, self.wavelength, self.izaDeg, self.iaaDeg, self.alphaDeg, self.betaDeg,
                                   verbose=self.verbose)
        elif self.__orient is 'AF':
            QS = XSEC_QS_S_WRAPPER(self.nmax, self.wavelength, self.izaDeg, self.iaaDeg, self.n_alpha, self.n_beta,
                                   self.or_pdf, verbose=self.verbose)
        else:
            raise ValueError("Orientation must be S or AF.")

        return QS

    def __QAS(self):
        """
        Asymetry cross section for the current setup, with polarization.
        """

        if self.__orient is 'S':
            QAS = XSEC_ASY_S_WRAPPER(self.nmax, self.wavelength, self.izaDeg, self.iaaDeg, self.alphaDeg, self.betaDeg,
                                     verbose=self.verbose)
        elif self.__orient is 'AF':
            QAS = XSEC_ASY_AF_WRAPPER(self.nmax, self.wavelength, self.izaDeg, self.iaaDeg, self.n_alpha, self.n_beta,
                                      self.or_pdf, verbose=self.verbose)
        else:
            raise ValueError("Orientation must be S or AF.")

        return QAS

    def __QE(self):
        """
        Extinction cross section for the current setup, with polarization.
        """

        S, Z = self.compute_SZ(vzaDeg=self.izaDeg, vaaDeg=self.iaaDeg)

        return XSEC_QE_WRAPPER(S, self.wavelength)

    def __I(self):
        """
        Scattering intensity (phase function) for the current setup.
        """
        Z = self.Z

        return XSEC_QSI_WRAPPER(Z)

    # ---- Other Functions ----
    def __get_pdf(self, pdf):
        """
        Auxiliary function to determine the PDF function.

        Parameters
        ----------
        pdf : {'gauss', 'uniform'}
            Particle orientation Probability Density Function (PDF) for orientational averaging:
                * 'gauss': Use a Gaussian PDF (default).
                * 'uniform': Use a uniform PDR.

        Returns
        -------
        function : callable

        """
        if callable(pdf):
            return pdf
        elif pdf is None or pdf is 'gauss':
            return Orientation.gaussian()
        elif pdf is 'uniform':
            return Orientation.uniform()
        else:
            raise AssertionError(
                "The Particle size distribution (psd) must be callable or 'None' to get the default gaussian psd.")

    def __property_return(self, X, normalize=True):
        if normalize:
            if self.normalize:
                # return X[0:-1] - X[-1]
                return X
            else:
                return X
        else:
            if self.normalize:
                # return X[0:-1]
                return X
            else:
                return X
